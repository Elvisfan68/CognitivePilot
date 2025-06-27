from psychopy import visual, core, event, data, gui
import random
import numpy as np
import os
from datetime import datetime
import csv
import pygame

class BART:
    def __init__(self):
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
        # Get participant info
        self.get_participant_info()
        
        # Initialize window FIRST - FULLSCREEN
        self.win = visual.Window(
            size=[1920, 1080],
            fullscr=True,
            screen=0,
            winType='pyglet',
            allowGUI=False,
            allowStencil=False,
            monitor='testMonitor',
            color=[-1, -1, -1],
            colorSpace='rgb',
            blendMode='avg',
            useFBO=True,
            units='pix'
        )

        self.win.mouseVisible = True
        self.calculate_text_scaling()

        # Automatic BART parameters
        self.array_size = 128
        self.points_per_pump = 0.01  # 1 cent per pump
        self.total_trials = 30
        
        # Generate break points for 30 trials with average of 64
        self.break_points = self.generate_break_points()
        
        # Slider control variables
        self.selected_pumps = 1
        self.slider_dragging = False
        
        # Pumping animation variables
        self.is_pumping = False
        self.pumps_to_simulate = 0
        self.pumps_simulated = 0
        self.pump_timer = 0
        self.pump_interval = 0.1  # Time between simulated pumps
        self.in_topoff_mode = False  # Track if we're in top-off mode
        
        # Initialize display elements
        self.setup_display()
        
        # Data storage
        self.trial_data = []
        self.total_earned = 0.0
        self.last_balloon_earned = 0.0
        self.temporary_bank = 0.0
        
        # Current trial variables
        self.current_trial = 0
        self.current_pumps = 0
        self.current_balloon_size = 50
        self.balloon_exploded = False
        
        # Track pump sessions within a trial
        self.pump_sessions = []  # List of individual pump sessions
        self.session_number = 0  # Current session number within trial
        self.has_topped_off = False  # Track if user has already topped off

        # Tracking variables for proper top-off logging
        self.intended_pumps_total = 0  # Track total intended pumps (initial + topoff)
        self.initial_pumps_selected = 0  # Track first session selection
        self.topoff_pumps_selected = 0  # Track topoff session selection
        self.current_session_is_topoff = False  # Track if current session is top-off
        
        # Trial sequence - 30 balloons total
        self.trial_sequence = self.create_trial_sequence()

        # Pre-generate top-off assignment: 15 True, 15 False, shuffled
        self.topoff_assignment = [True]*15 + [False]*15
        random.shuffle(self.topoff_assignment)
        
        # 1. Find indices of the three highest break points
        break_points = [trial['explosion_point'] for trial in self.trial_sequence]
        sorted_indices = sorted(range(len(break_points)), key=lambda i: break_points[i], reverse=True)
        guaranteed_topoff_indices = sorted_indices[:3]
        print(guaranteed_topoff_indices)
        # 2. Choose 12 more random indices from the rest
        remaining_indices = [i for i in range(len(break_points)) if i not in guaranteed_topoff_indices]
        random_topoff_indices = random.sample(remaining_indices, 12)

        # 3. Combine for a total of 15 top-off indices
        final_topoff_indices = set(guaranteed_topoff_indices + random_topoff_indices)

        # 4. Create the assignment list
        self.topoff_assignment = [i in final_topoff_indices for i in range(len(break_points))]
        print(self.topoff_assignment)
        try:
            self.pump_sound = pygame.mixer.Sound("./Sound Effects/pump.mp3")
            self.pop_sound = pygame.mixer.Sound("./Sound Effects/pop.mp3") 
            self.collect_sound = pygame.mixer.Sound("./Sound Effects/collect.mp3")
            print("Sounds loaded successfully")
        except Exception as e:
            print(f"Warning: Could not load sounds: {e}")
            self.pump_sound = None
            self.pop_sound = None
            self.collect_sound = None
    
    def get_participant_info(self):
        """Get participant information"""
        try:
            dlg = gui.Dlg(title="Automatic BART - Participant Info")
            dlg.addField('Participant ID:')
            dlg.addField('Treatment:')
            dlg.show()
            
            if dlg.OK:
                self.participant_id = str(dlg.data[0]) if dlg.data[0] else "test_participant"
                self.treatment = str(dlg.data[1]) if dlg.data[1] else "unknown"
            else:
                core.quit()
        except:
            # Fallback if GUI doesn't work
            self.participant_id = "test_participant"
            self.treatment = "unknown"

    def play_sound(self, sound_name):
        """Function to play pre-loaded sounds"""
        try:
            if sound_name == "pump.mp3" and self.pump_sound:
                self.pump_sound.stop()
                self.pump_sound.play()
            elif sound_name == "pop.mp3" and self.pop_sound:
                self.pop_sound.stop()
                self.pop_sound.play()
            elif sound_name == "collect.mp3" and self.collect_sound:
                self.collect_sound.stop()
                self.collect_sound.play()
        except Exception as e:
            print(f"Error playing sound {sound_name}: {e}")
            pass

    def calculate_balloon_color(self, pump_count):
        """Calculate balloon color based on pump count (green -> yellow -> red)"""
        # Normalize pump count to 0-1 range (assuming max useful range is ~100 pumps)
        max_pumps = 100
        ratio = min(pump_count / max_pumps, 1.0)
        
        if ratio <= 0.5:
            # Green to Yellow (0 to 50 pumps)
            # Green: (0, 1, 0) to Yellow: (1, 1, 0)
            local_ratio = ratio * 2  # 0 to 1
            r = local_ratio
            g = 1.0
            b = 0.0
        else:
            # Yellow to Red (50 to 100+ pumps)
            # Yellow: (1, 1, 0) to Red: (1, 0, 0)
            local_ratio = (ratio - 0.5) * 2  # 0 to 1
            r = 1.0
            g = 1.0 - local_ratio
            b = 0.0
        
        return [r * 2 - 1, g * 2 - 1, b * 2 - 1]  # Convert to PsychoPy range (-1 to 1)

    def generate_break_points(self):
        """Generate break point sequences for 30 trials: 3 blocks of 10, each with average of 64"""
        print(f"\nGenerating break points for {self.total_trials} trials (3 blocks of 10)")
        
        all_break_points = []
        
        # Generate 3 blocks of 10 trials each
        for block_num in range(3):
            print(f"Generating Block {block_num + 1}...")
            
            # Generate 10 break points with average of 64 for this block
            block_break_points = self.generate_sequence_with_exact_average(self.array_size, 64, 10)
            
            # Verify this block's average
            block_avg = np.mean(block_break_points)
            print(f"  Block {block_num + 1} break points: {block_break_points}")
            print(f"  Block {block_num + 1} average: {block_avg:.3f}")
            
            # Add to overall list
            all_break_points.extend(block_break_points)
        
        # Verify overall average
        overall_avg = np.mean(all_break_points)
        print(f"\nOverall average across all 30 trials: {overall_avg:.3f}")
        print(f"All break points: {all_break_points}")
        
        return all_break_points

    def generate_sequence_with_exact_average(self, array_size, target_avg, sequence_length):
        """Generate a sequence of break points with exact target average"""
        max_attempts = 10000
        
        for attempt in range(max_attempts):
            # Start with the target average for all positions
            sequence = [target_avg] * sequence_length
            
            # Add random variation while maintaining the exact sum
            target_sum = target_avg * sequence_length
            
            # Make random swaps to add variation
            for _ in range(sequence_length * 2):
                # Pick two random positions
                i, j = random.sample(range(sequence_length), 2)
                
                # Try to make a random change that preserves the sum
                max_change = min(
                    sequence[i] - 1,           # Can't go below 1
                    array_size - sequence[j],  # Can't go above array_size
                    sequence[j] - 1,           # Can't go below 1
                    array_size - sequence[i]   # Can't go above array_size
                )
                
                if max_change > 0:
                    change = random.randint(1, max_change)
                    
                    # Randomly decide direction
                    if random.choice([True, False]):
                        sequence[i] += change
                        sequence[j] -= change
                    else:
                        sequence[i] -= change
                        sequence[j] += change
            
            # Ensure all values are in valid range
            sequence = [max(1, min(array_size, x)) for x in sequence]
            
            # Adjust to get exact average
            current_sum = sum(sequence)
            difference = target_sum - current_sum
            
            # Distribute the difference across random positions
            attempts_to_fix = 100
            for _ in range(attempts_to_fix):
                if difference == 0:
                    break
                    
                pos = random.randint(0, sequence_length - 1)
                
                if difference > 0:  # Need to increase sum
                    increase = min(difference, array_size - sequence[pos])
                    sequence[pos] += increase
                    difference -= increase
                elif difference < 0:  # Need to decrease sum
                    decrease = min(-difference, sequence[pos] - 1)
                    sequence[pos] -= decrease
                    difference += decrease
            
            # Check if we achieved the exact average
            if abs(sum(sequence) - target_sum) < 0.001:
                actual_avg = sum(sequence) / sequence_length
                if abs(actual_avg - target_avg) < 0.001:
                    return sequence
        
        # Fallback
        print(f"Warning: Using fallback method for sequence generation")
        return self.create_fallback_sequence(array_size, target_avg, sequence_length)

    def create_fallback_sequence(self, array_size, target_avg, sequence_length):
        """Create a sequence with exact average using a deterministic method"""
        target_sum = target_avg * sequence_length
        
        # Start with all values at target_avg (rounded down)
        base_value = int(target_avg)
        sequence = [base_value] * sequence_length
        
        # Calculate how much we need to add to reach the exact sum
        current_sum = sum(sequence)
        remainder = target_sum - current_sum
        
        # Distribute the remainder
        positions = list(range(sequence_length))
        random.shuffle(positions)
        
        for i, pos in enumerate(positions):
            if remainder <= 0:
                break
            
            if sequence[pos] < array_size:
                add_amount = min(1, remainder, array_size - sequence[pos])
                sequence[pos] += add_amount
                remainder -= add_amount
        
        return sequence

    def create_trial_sequence(self):
        """Create the trial sequence: 30 balloons total"""
        sequence = []
        
        # Create 30 trials
        for i in range(self.total_trials):
            sequence.append({
                'trial': i + 1,
                'explosion_point': self.break_points[i]
            })
        
        return sequence
    
    def calculate_text_scaling(self):
        """Calculate text sizes based on screen dimensions"""
        screen_width = self.win.size[0]
        screen_height = self.win.size[1]
        
        base_scale = 1.5
        scale_factor = (screen_height / 1080.0) * base_scale
        
        self.text_sizes = {
            'large': int(35 * scale_factor),
            'medium': int(28 * scale_factor),
            'normal': int(22 * scale_factor),
            'small': int(18 * scale_factor),
            'button': int(24 * scale_factor),
            'huge': int(50 * scale_factor)
        }
        
        print(f"Screen size: {screen_width}x{screen_height}")
        print(f"Scale factor: {scale_factor:.2f}")
        print(f"Text sizes: {self.text_sizes}")

    def update_slider_position(self):
        """Update slider handle position based on selected pumps"""
        if self.in_topoff_mode:
            # Top-off mode: 1-9 pumps
            pump_ratio = (self.selected_pumps - 1) / 8  # 8 = range from 1-9
        else:
            # Normal mode: 1-128 pumps
            pump_ratio = (self.selected_pumps - 1) / 127  # 127 = range from 1-128
        
        # Calculate handle position along slider track
        handle_x = self.slider_left + pump_ratio * self.slider_width
        self.slider_handle.pos = [handle_x, self.slider_y]

    def calculate_predicted_balloon_size(self):
        """Calculate what balloon size would be after pumping selected amount"""
        if self.in_topoff_mode:
            # For top-off, show what size would be after adding more pumps to current total
            total_pumps_after_topoff = self.current_pumps + self.selected_pumps
            predicted_size = 50 + (total_pumps_after_topoff * 8)
        else:
            # For initial pump, start from base balloon size (50)
            predicted_size = 50 + (self.selected_pumps * 8)
        
        return predicted_size

    def setup_display(self):
        """Setup all display elements with slider control and balloon preview"""
        screen_width = self.win.size[0]
        screen_height = self.win.size[1]
        scale_factor = (screen_height / 1080.0) * 1.5
        
        # Button dimensions
        pump_button_width = int(200 * scale_factor)
        pump_button_height = int(70 * scale_factor)
        collect_button_width = int(240 * scale_factor)
        collect_button_height = int(70 * scale_factor)
        
        # Button positions
        pump_button_x = -screen_width // 3
        collect_button_x = screen_width // 3
        button_y = -screen_height // 3
        
        # Slider position (above buttons)
        slider_y = button_y + int(200 * scale_factor)
        slider_width = int(400 * scale_factor)
        slider_height = int(20 * scale_factor)
        
        # Balloon (higher position)
        balloon_y = int(150 * scale_factor)
        self.balloon = visual.Circle(
            self.win,
            radius=50,
            pos=[0, balloon_y],
            fillColor=[-1, 1, -1],  # Start green
            lineColor=[-1, 0.4, -1],  # Dark green
            lineWidth=2
        )
        
        # Balloon preview outline (shows predicted size)
        self.balloon_preview = visual.Circle(
            self.win,
            radius=50,
            pos=[0, balloon_y],
            fillColor=None,
            lineColor=[-1, 1, -1],  # Start green
            lineWidth=2,
            opacity=0.5
        )
        
        # Slider elements
        self.slider_y = slider_y
        self.slider_width = slider_width
        self.slider_left = -slider_width // 2
        self.slider_right = slider_width // 2
        
        # Slider track (background bar)
        self .slider_track = visual.Rect(
            self.win,
            width=slider_width,
            height=slider_height,
            pos=[0, slider_y],
            fillColor='lightgray',
            lineColor='black',
            lineWidth=2
        )
        
        # Slider handle (draggable circle)
        self.slider_handle = visual.Circle(
            self.win,
            radius=int(15 * scale_factor),
            pos=[self.slider_left, slider_y],
            fillColor='red',
            lineColor='darkred',
            lineWidth=3
        )
        
        # Pump count display (below slider)
        self.pump_count_text = visual.TextStim(
            self.win,
            text='Pumps: 1',
            pos=[0, slider_y - int(50 * scale_factor)],
            color='white',
            height=self.text_sizes['medium'],
            bold=True
        )
        
        # Pump button (LEFT)
        self.pump_button = visual.Rect(
            self.win,
            width=pump_button_width,
            height=pump_button_height,
            pos=[pump_button_x, button_y],
            fillColor='red',
            lineColor='darkred',
            lineWidth=4
        )
        
        self.pump_button_text = visual.TextStim(
            self.win,
            text='PUMP',
            pos=[pump_button_x, button_y],
            color='white',
            height=self.text_sizes['button'],
            bold=True
        )
        
        # Collect button (RIGHT)
        self.collect_button = visual.Rect(
            self.win,
            width=collect_button_width,
            height=collect_button_height,
            pos=[collect_button_x, button_y],
            fillColor='green',
            lineColor='darkgreen',
            lineWidth=4
        )
        
        self.collect_text = visual.TextStim(
            self.win,
            text='Collect $$$',
            pos=[collect_button_x, button_y],
            color='white',
            height=self.text_sizes['button'],
            bold=True
        )
        
        # Store button info for click detection
        self.pump_button_info = {
            'x': pump_button_x, 'y': button_y,
            'width': pump_button_width, 'height': pump_button_height
        }
        
        self.collect_button_info = {
            'x': collect_button_x, 'y': button_y,
            'width': collect_button_width, 'height': collect_button_height
        }
        
        # Status bar at top
        status_y = screen_height // 3
        self.total_earned_text = visual.TextStim(
            self.win, text='Total Earned: $0.00',
            pos=[-screen_width // 3, status_y],
            color='white',
            height=self.text_sizes['medium'],
            bold=True
        )
        
        self.last_balloon_text = visual.TextStim(
            self.win,
            text='Last Balloon: $0.00',
            pos=[screen_width // 3, status_y],
            color='white',
            height=self.text_sizes['medium'],
            bold=True
        )
        
        self.trial_number_text = visual.TextStim(
            self.win,
            text='Balloon 1 of 30',
            pos=[0, status_y],
            color='white',
            height=self.text_sizes['medium'],
            bold=True
        )
        
        # Instructions below buttons
        instruction_y = button_y - int(100 * scale_factor)
        min_instruction_y = -screen_height // 2 + int(50 * scale_factor)
        instruction_y = max(instruction_y, min_instruction_y)
        
        self.instruction_text = visual.TextStim(
            self.win,
            text='',
            pos=[0, instruction_y],
            color='white',
            height=self.text_sizes['small'],
            wrapWidth=screen_width * 0.8,
            alignText='center'
        )
            
    def show_instructions(self):
        """Show task instructions"""
        instructions = [
            "Welcome to the Balloon Analogue Risk Task (BART)\n\n" +
            "In this task, you will pump up balloons to earn money.\n\n" +
            "Press SPACE to continue...",
            
            "Each pump earns you 1 cent.\n\n" +
            "The money goes into a temporary bank that you can collect at any time.\n\n" +
            "Press SPACE to continue...",
            
            "BUT BE CAREFUL!\n\n" +
            "If you pump too much, the balloon will pop and you'll lose\n" +
            "all the money in your temporary bank for that balloon.\n\n" +
            "Press SPACE to continue...",
            
            "Different strategies work for different people.\n" +
            "You will complete 30 balloons total.\n\n" +
            "Press SPACE to continue...",
            
            "CONTROLS:\n\n" +
            "• Drag the slider to select number of pumps (1-128)\n" +
            "• The outline shows predicted balloon size\n" +
            "• Click PUMP to pump that many times\n" +
            "• After first pump, you can 'top off' with 1-9 more pumps\n" +
            "• Click 'Collect $$$' to collect and move to next balloon\n\n" +
            "Try to earn as much money as possible!\n\n" +
            "Press SPACE to begin..."
        ]
        
        instruction_display = visual.TextStim(
            self.win,
            text='',
            pos=[0, 0],
            color='white',
            height=self.text_sizes['large'],
            wrapWidth=1200
        )
        
        for instruction in instructions:
            instruction_display.text = instruction
            instruction_display.draw()
            self.win.flip()
            
            keys = event.waitKeys(keyList=['space', 'escape'])
            if keys and 'escape' in keys:
                self.quit_experiment()

    def start_new_balloon(self):
        """Initialize a new balloon"""
        if self.current_trial >= self.total_trials:
            self.end_experiment()
            return
        
        # Reset balloon state
        self.current_pumps = 0
        self.current_balloon_size = 50
        self.temporary_bank = 0.0
        self.balloon_exploded = False
        self.is_pumping = False
        self.in_topoff_mode = False
        self.has_topped_off = False
        
        # Reset intended pump tracking
        self.intended_pumps_total = 0
        self.initial_pumps_selected = 0
        self.topoff_pumps_selected = 0
        self.current_session_is_topoff = False
        
        # Reset session tracking
        self.pump_sessions = []
        self.session_number = 0
        
        # Reset balloon appearance to green (0 pumps)
        self.balloon.fillColor = [-1, 1, -1]  # Green in PsychoPy coordinates
        self.balloon.lineColor = [-1, 0.4, -1]  # Dark green
        self.balloon.radius = self.current_balloon_size
        
        # Reset preview to green
        self.balloon_preview.lineColor = [-1, 1, -1]  # Green
        
        # Reset slider to 1
        self.selected_pumps = 1
        self.update_slider_position()
        
        # Update displays
        self.update_displays()

    def handle_slider_interaction(self, mouse_pos, mouse_pressed):
        """Handle slider interaction for selecting pump count"""
        if self.is_pumping:  # Don't allow slider interaction during pumping
            return
            
        mouse_x, mouse_y = mouse_pos
        
        # Check if mouse is over slider area (expanded hitbox)
        slider_hitbox_height = 60  # Larger area for easier clicking
        if (self.slider_left - 20 <= mouse_x <= self.slider_right + 20 and
            self.slider_y - slider_hitbox_height//2 <= mouse_y <= self.slider_y + slider_hitbox_height//2):
            
            if mouse_pressed and not self.slider_dragging:
                self.slider_dragging = True
                
            if self.slider_dragging:
                # Calculate position along slider (clamp to slider bounds)
                relative_x = max(0, min(self.slider_width, mouse_x - self.slider_left))
                slider_ratio = relative_x / self.slider_width
                
                if self.in_topoff_mode:
                    # Top-off mode: 1-9 pumps (9 total values)
                    new_pumps = max(1, min(9, int(1 + slider_ratio * 8 + 0.5)))  # +0.5 for rounding
                else:
                    # Normal mode: 1-128 pumps (128 total values)
                    new_pumps = max(1, min(128, int(1 + slider_ratio * 127 + 0.5)))  # +0.5 for rounding
                
                if new_pumps != self.selected_pumps:
                    self.selected_pumps = new_pumps
                    self.update_slider_position()
                    
                    # UPDATE BOTH SIZE AND COLOR FOR PREVIEW
                    predicted_size = self.calculate_predicted_balloon_size()
                    self.balloon_preview.radius = predicted_size
                    
                    # Calculate predicted pump count for preview color
                    if self.in_topoff_mode:
                        predicted_pumps = self.current_pumps + self.selected_pumps
                    else:
                        predicted_pumps = self.selected_pumps
                    
                    # Update preview circle color
                    preview_color = self.calculate_balloon_color(predicted_pumps)
                    self.balloon_preview.lineColor = preview_color
                    
                    print(f"DEBUG: Updated preview to {predicted_size} pixels, color for {predicted_pumps} pumps")
                    
                    # Update text
                    self.pump_count_text.text = f'Pumps: {self.selected_pumps}'
        
        if not mouse_pressed:
            self.slider_dragging = False
    def start_pump_simulation(self):
        """Start the automatic pumping simulation"""
        if self.is_pumping:
            return
        
        # Track intended pumps based on session
        if self.session_number == 0:  # First session
            self.initial_pumps_selected = self.selected_pumps
            self.intended_pumps_total = self.selected_pumps
            self.current_session_is_topoff = False
        elif self.in_topoff_mode:  # Top-off session
            self.topoff_pumps_selected = self.selected_pumps
            self.intended_pumps_total = self.initial_pumps_selected + self.selected_pumps
            self.current_session_is_topoff = True
        
        # Validate pump selection for top-off mode
        if self.in_topoff_mode and self.selected_pumps > 9:
            self.selected_pumps = 9
            self.topoff_pumps_selected = 9
            self.intended_pumps_total = self.initial_pumps_selected + 9
            self.update_slider_position()
            
        # Start pumping simulation
        self.is_pumping = True
        self.pumps_to_simulate = self.selected_pumps
        self.pumps_simulated = 0
        self.pump_timer = core.getTime()
        
        print(f"Adding {self.pumps_to_simulate} more pumps. Current total: {self.current_pumps}")
        print(f"Intended total: {self.intended_pumps_total}")
        print(f"Is top-off session: {self.current_session_is_topoff}")

    def update_pump_simulation(self):
        """Update the pumping simulation"""
        if not self.is_pumping:
            return False
            
        current_time = core.getTime()
        
        if current_time - self.pump_timer >= self.pump_interval:
            # Time for next pump
            self.pumps_simulated += 1
            self.current_pumps += 1
            
            # Check explosion first
            trial_info = self.trial_sequence[self.current_trial]
            explosion_point = trial_info['explosion_point']
            
            if self.current_pumps >= explosion_point:
                # Balloon pops during simulation
                self.temporary_bank += self.points_per_pump
                self.current_balloon_size += 8
                self.balloon_pop()
                return False
            
            # Successful pump
            self.play_sound("pump.mp3")
            
            # Increase balloon size
            self.current_balloon_size += 8
            self.balloon.radius = self.current_balloon_size
            
            # Add money to temporary bank
            self.temporary_bank += self.points_per_pump
            
            # Update display
            self.update_displays()
            
            # Reset timer
            self.pump_timer = current_time
            
            # Check if simulation complete
            if self.pumps_simulated >= self.pumps_to_simulate:
                self.is_pumping = False
                
                # Record this pump session with INTENDED pumps
                self.record_pump_session_data_only()
                
                # Handle post-session logic based on session type
                if self.current_session_is_topoff:
                    # Top-off session completed - auto-collect
                    print("Top-off session completed - auto-collecting money")
                    core.wait(0.5)
                    self.collect_money_after_topoff()
                else:
                    # First session completed - show top-off option if assigned for this trial
                    if self.session_number == 1 and not self.has_topped_off:
                        # Use pre-generated assignment for this trial
                        if self.topoff_assignment[self.current_trial]:
                            print("DEBUG: Showing top-off option (assigned)")
                            self.show_topoff_option()
                        else:
                            print("DEBUG: Skipping top-off, auto-collecting (assigned)")
                            core.wait(0.5)
                            self.collect_money()
                    else:
                        print("DEBUG: Not showing top-off")
                
                return False
        
        return True

    def record_pump_session_data_only(self):
        """Record pump session data without triggering any other actions"""
        trial_info = self.trial_sequence[self.current_trial]
        
        self.session_number += 1
        was_topoff_session = self.current_session_is_topoff
        
        print(f"Recording session {self.session_number}: was_topoff={was_topoff_session}, INTENDED_pumps={self.selected_pumps}")
        
        # Record the session data with INTENDED pumps
        session_data = {
            'participant_id': self.participant_id,
            'treatment': self.treatment,
            'trial': self.current_trial + 1,
            'session': self.session_number,
            'explosion_point': trial_info['explosion_point'],
            'pumps_selected_this_session': self.selected_pumps,  # INTENDED pumps
            'pumps_actual_this_session': self.pumps_simulated,   # ACTUAL pumps
            'total_pumps_so_far': self.current_pumps,
            'temporary_bank': self.temporary_bank,
            'was_topoff': was_topoff_session,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.pump_sessions.append(session_data)
        print(f"Session {self.session_number}: INTENDED {self.selected_pumps}, ACTUAL {self.pumps_simulated}, was_topoff: {was_topoff_session}")
        
        # Mark top-off as used if this was a top-off session
        if was_topoff_session:
            self.has_topped_off = True
            self.in_topoff_mode = False

    def show_topoff_option(self):
        """Show option to add 1-9 more pumps after first session"""
        # Limit slider to 1-9 pumps for top-off
        self.in_topoff_mode = True
        self.selected_pumps = 1  # Reset to 1
        self.update_slider_position()
        
        # Update displays to show top-off mode
        self.update_displays()

    def collect_money(self):
        """Collect money from temporary bank"""
        if self .temporary_bank > 0 and not self.is_pumping:
            # Exit top-off mode
            self.in_topoff_mode = False
            
            # Track last balloon info
            self.last_balloon_pumps = self.intended_pumps_total
            self.last_balloon_exploded = False
            print(f"DEBUG: Collecting - tracking INTENDED {self.intended_pumps_total} pumps (actual: {self.current_pumps})")
            
            # Play collection sound and animate money transfer
            self.animate_money_collection()
            
            # Transfer money
            self.last_balloon_earned = self.temporary_bank
            self.total_earned += self.temporary_bank
            
            # Record trial data
            self.record_trial_data(exploded=False)
            
            # Reset temporary bank
            self.temporary_bank = 0.0
            
            # Move to next trial
            self.current_trial += 1
            self.start_new_balloon()

    def collect_money_after_topoff(self):
        """Auto-collect money after top-off session"""
        if self.temporary_bank > 0:
            # Track last balloon info
            self.last_balloon_pumps = self.intended_pumps_total
            self.last_balloon_exploded = False
            print(f"DEBUG: Auto-collecting after topoff - tracking INTENDED {self.intended_pumps_total} pumps (actual: {self.current_pumps})")
            
            # Play collection sound and animate money transfer
            self.animate_money_collection()
            
            # Transfer money
            self.last_balloon_earned = self.temporary_bank
            self.total_earned += self.temporary_bank
            
            # Record trial data
            self.record_trial_data(exploded=False)
            
            # Reset temporary bank
            self.temporary_bank = 0.0
            
            # Move to next trial
            self.current_trial += 1
            self.start_new_balloon()

    def balloon_pop(self):
        """Handle balloon explosion"""
        self.balloon_exploded = True
        self.is_pumping = False
        self.play_sound("pop.mp3")
        
        # Record the current pump session with INTENDED pumps (for explosions)
        self.record_explosion_session()
        
        # Track last balloon info
        self.last_balloon_pumps = self.intended_pumps_total
        self.last_balloon_exploded = True
        self.last_balloon_earned = 0.0
        print(f"DEBUG: Exploding - tracking INTENDED {self.intended_pumps_total} pumps (actual: {self.current_pumps})")
        
        # Show explosion effect
        self.show_explosion()
        
        # Record trial data
        self.record_trial_data(exploded=True)
        
        # Reset temporary bank
        self.temporary_bank = 0.0
        
        # Move to next trial
        self.current_trial += 1
        core.wait(1.0)
        self.start_new_balloon()

    def record_explosion_session(self):
        """Record pump session when balloon explodes during pumping"""
        trial_info = self.trial_sequence[self.current_trial]
        
        self.session_number += 1
        was_topoff_session = self.current_session_is_topoff
        
        print(f"Recording EXPLOSION session {self.session_number}: was_topoff={was_topoff_session}, INTENDED_pumps={self.selected_pumps}")
        
        # Record the INTENDED pumps, not what actually happened
        session_data = {
            'participant_id': self.participant_id,
            'treatment': self.treatment,
            'trial': self.current_trial + 1,
            'session': self.session_number,
            'explosion_point': trial_info['explosion_point'],
            'pumps_selected_this_session': self.selected_pumps,  # INTENDED pumps
            'pumps_actual_this_session': self.pumps_simulated,   # ACTUAL pumps before explosion
            'total_pumps_so_far': self.current_pumps,
            'temporary_bank': self.temporary_bank,
            'was_topoff': was_topoff_session,
            'exploded_during_session': True,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.pump_sessions.append(session_data)
        print(f"EXPLOSION Session {self.session_number}: INTENDED {self.selected_pumps}, ACTUAL {self.pumps_simulated}, was_topoff: {was_topoff_session}")
        
        # Mark top-off as used if this was a top-off session that exploded
        if was_topoff_session:
            self.has_topped_off = True
            self.in_topoff_mode = False

    def show_explosion(self):
        """Show balloon explosion animation"""
        explosion = visual.Circle(
            self.win,
            radius=self.current_balloon_size * 1.5,
            pos=self.balloon.pos,
            fillColor='red',
            lineColor='darkred'
        )
        
        pop_text = visual.TextStim(
            self.win,
            text='POP!',
            pos=self.balloon.pos,
            color='white',
            height=self.text_sizes['huge']
        )
        
        # Flash effect
        for _ in range(3):
            explosion.draw()
            pop_text.draw()
            self.draw_ui()
            self.win.flip()
            core.wait(0.1)
            
            self.draw_ui()
            self.win.flip()
            core.wait(0.1)

    def animate_money_collection(self):
        """Animate money being transferred to total"""
        self.play_sound("collect.mp3")
        
        original_total = self.total_earned
        steps = 20
        
        for i in range(steps + 1):
            current_transfer = (self.temporary_bank / steps) * i
            display_total = original_total + current_transfer
            
            temp_text = f'Total Earned: ${display_total:.2f}'
            self.total_earned_text.text = temp_text
            
            self.draw_balloon()
            self.draw_ui()
            self.win.flip()
            core.wait(0.05)
    
    def record_trial_data(self, exploded):
        """Record data for current trial including all pump sessions"""
        trial_info = self.trial_sequence[self.current_trial]
        
        print(f"Recording trial data for trial {self.current_trial + 1}")
        print(f"Current pump_sessions: {self.pump_sessions}")
        print(f"Has topped off: {self.has_topped_off}")
        
        # Main trial record
        data_row = {
            'participant_id': self.participant_id,
            'treatment': self.treatment,
            'trial': self.current_trial + 1,
            'explosion_point': trial_info['explosion_point'],
            'total_pump_sessions': len(self.pump_sessions),
            'total_pumps_final': self.current_pumps,
            'exploded': exploded,
            'earned_this_balloon': 0.0 if exploded else self.temporary_bank,
            'total_earned': self.total_earned,
            'used_topoff': self.has_topped_off,
            'pump_sessions_detail': str(self.pump_sessions),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.trial_data.append(data_row)
        print(f"Trial {self.current_trial + 1} recorded with {len(self.pump_sessions)} sessions")

    def update_displays(self):
        """Update all display texts and balloon preview"""
        self.total_earned_text.text = f'Total Earned: ${self.total_earned:.2f}'
        
        # Enhanced last balloon display
        if self.current_trial > 0:
            if hasattr(self, 'last_balloon_exploded') and self.last_balloon_exploded:
                trial_info = self.trial_sequence[self.current_trial - 1]
                explosion_point = trial_info['explosion_point']
                self.last_balloon_text.text = f'Last: ${self.last_balloon_earned:.2f}\nYou pumped: {getattr(self, "last_balloon_pumps", 0)}\nPopped at: {explosion_point}'
            else:
                self.last_balloon_text.text = f'Last: ${getattr(self, "last_balloon_earned", 0.0):.2f}\nYou pumped: {getattr(self, "last_balloon_pumps", 0)}'
        else:
            self.last_balloon_text.text = 'Last Balloon: $0.00'
        
        self.trial_number_text.text = f'Balloon {self.current_trial + 1} of {self.total_trials}'
        
        # Update pump count display
        if self.in_topoff_mode:
            self.pump_count_text.text = f'Pumps: {self.selected_pumps}'
        else:
            self.pump_count_text.text = f'Pumps: {self.selected_pumps}'
        
        # Update balloon preview size and colors (ONLY when not pumping)
        if not self.is_pumping:
            # Update preview circle size
            predicted_size = self.calculate_predicted_balloon_size()
            self.balloon_preview.radius = predicted_size
            
            # Calculate predicted pump count for preview color
            if self.in_topoff_mode:
                predicted_pumps = self.current_pumps + self.selected_pumps
            else:
                predicted_pumps = self.selected_pumps
            
            # Update preview circle color
            preview_color = self.calculate_balloon_color(predicted_pumps)
            self.balloon_preview.lineColor = preview_color
        
        # Update actual balloon color based on current pumps (always update)
        if self.current_pumps > 0:
            balloon_color = self.calculate_balloon_color(self.current_pumps)
            self.balloon.fillColor = balloon_color
            # Make outline slightly darker
            outline_color = [c * 0.7 for c in balloon_color]
            self.balloon.lineColor = outline_color
        
        # Instruction text
        if self.is_pumping:
            instruction_lines = [
                f'Pumping: {self.pumps_simulated}/{self.pumps_to_simulate}',
                f'Total: {self.current_pumps}',
                f'Temp Bank: ${self.temporary_bank:.2f}'
            ]
            self.instruction_text.text = '\n'.join(instruction_lines)
        elif self.in_topoff_mode:
            instruction_lines = [
                'TOP-OFF: Add 1-9 more pumps?',
                f'Total: {self.current_pumps}',
                f'Temp Bank: ${self.temporary_bank:.2f}',
                'PUMP to add or COLLECT to finish'
            ]
            self.instruction_text.text = '\n'.join(instruction_lines)
        elif self.current_pumps > 0:
            if self.has_topped_off:
                instruction_lines = [
                    f'Total: {self.current_pumps}',
                    f'Temp Bank: ${self.temporary_bank:.2f}',
                    'Top-off used - COLLECT to finish'
                ]
            else:
                instruction_lines = [
                    f'Total: {self.current_pumps}',
                    f'Temp Bank: ${self.temporary_bank:.2f}',
                    'COLLECT to finish'
                ]
            self.instruction_text.text = '\n'.join(instruction_lines)
        else:
            instruction_lines = [
                'Drag slider to select pumps, then PUMP',
                f'Temp Bank: ${self.temporary_bank:.2f}'
            ]
            self.instruction_text.text = '\n'.join(instruction_lines)
    def draw_balloon(self):
        """Draw the balloon and preview"""
        # Draw preview outline first (behind balloon)
        if not self.balloon_exploded:
            self.balloon_preview.draw()
            self.balloon.draw()
    
    def draw_ui(self):
        """Draw all UI elements"""
        # Draw slider control
        self.slider_track.draw()
        self.slider_handle.draw()
        self.pump_count_text.draw()
        
        # Draw buttons
        self.pump_button.draw()
        self.pump_button_text.draw()
        self.collect_button.draw()
        self.collect_text.draw()
        
        # Draw text displays
        self.total_earned_text.draw()
        self.last_balloon_text.draw()
        self.trial_number_text.draw()
        self.instruction_text.draw()
    
    def handle_mouse_click(self, pos):
        """Handle mouse clicks on buttons"""
        if self.is_pumping:
            return
            
        mouse_x, mouse_y = pos
        
        # Check pump button
        pump = self.pump_button_info
        if (pump['x'] - pump['width']//2 < mouse_x < pump['x'] + pump['width']//2 and
            pump['y'] - pump['height']//2 < mouse_y < pump['y'] + pump['height']//2):
            print(f"Pump button clicked! Starting simulation with {self.selected_pumps} pumps")
            self.start_pump_simulation()
            return
        
        # Check collect button  
        collect = self.collect_button_info
        if (collect['x'] - collect['width']//2 < mouse_x < collect['x'] + collect['width']//2 and
            collect['y'] - collect['height']//2 < mouse_y < collect['y'] + collect['height']//2):
            print("Collect button clicked!")
            self.collect_money()
            return
        
    def run_trial_loop(self):
        """Main trial loop"""
        mouse_pressed = False
        
        while self.current_trial < self.total_trials:
            # Handle events
            mouse = event.Mouse()
            keys = event.getKeys(keyList=['escape'])
            
            # Handle keyboard input
            if keys:
                if 'escape' in keys:
                    self.quit_experiment()
            
            # Handle mouse interactions
            mouse_pos = mouse.getPos()
            mouse_buttons = mouse.getPressed()
            current_mouse_pressed = mouse_buttons[0]
            
            # Handle slider interaction
            self.handle_slider_interaction(mouse_pos, current_mouse_pressed)
            
            # Handle mouse clicks (only on button press, not hold)
            if current_mouse_pressed and not mouse_pressed:
                self.handle_mouse_click(mouse_pos)
            
            mouse_pressed = current_mouse_pressed
            
            # Update pumping simulation
            self.update_pump_simulation()
            
            # Draw everything
            self.draw_balloon()
            self.draw_ui()
            self.win.flip()
            
            # Small delay to prevent excessive CPU usage
            core.wait(0.01)

    def end_experiment(self):
        """End the experiment and show results"""
        # Calculate statistics
        all_pumps = [trial['total_pumps_final'] for trial in self.trial_data]
        mean_total_pumps = np.mean(all_pumps) if all_pumps else 0
        
        # Block analysis
        block1_pumps = [trial['total_pumps_final'] for trial in self.trial_data[0:10]]
        block2_pumps = [trial['total_pumps_final'] for trial in self.trial_data[10:20]]
        block3_pumps = [trial['total_pumps_final'] for trial in self.trial_data[20:30]]
        
        mean_block1 = np.mean(block1_pumps) if block1_pumps else 0
        mean_block2 = np.mean(block2_pumps) if block2_pumps else 0
        mean_block3 = np.mean(block3_pumps) if block3_pumps else 0
        
        # Explosion analysis
        total_explosions = sum(1 for trial in self.trial_data if trial['exploded'])
        
        # Top-off usage analysis
        topoff_usage = sum(1 for trial in self.trial_data if trial.get('used_topoff', False))
        
        # Show final results
        results_text = f"""Experiment Complete!
        
    PRIMARY MEASURE:
    Mean Total Pumps: {mean_total_pumps:.2f}
    
    BLOCK ANALYSIS:
    Block 1 (1-10): {mean_block1:.2f} pumps
    Block 2 (11-20): {mean_block2:.2f} pumps  
    Block 3 (21-30): {mean_block3:.2f} pumps
    
    Total Earned: ${self.total_earned:.2f}
    Total Explosions: {total_explosions}
    Top-offs Used: {topoff_usage} balloons
    
    Thank you for participating!
    
    Press SPACE to exit."""
        
        # Create results display
        results_display = visual.TextStim(
            self.win,
            text=results_text,
            pos=[0, 0],
            color='white',
            height=self.text_sizes['large'],
            wrapWidth=1200
        )
        
        # Clear screen and show results
        self.win.clearBuffer()
        results_display.draw()
        self.win.flip()
        
        # Wait for spacebar
        event.waitKeys(keyList=['space'])
        
        # Save data
        self.save_data()
        
        # Close
        self.win.close()
        core.quit()

    def save_data(self):
        """Save experimental data to single simplified CSV file"""
        filename = f"BART_TopOff_data_{self.participant_id}_{self.treatment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Create data directory if it doesn't exist
        if not os.path.exists('Bart Data'):
            os.makedirs('Bart Data')
        
        filepath = os.path.join('Bart Data', filename)
        
        # Create simplified data structure
        simplified_data = []
        
        for trial in self.trial_data:
            # Parse pump sessions to extract initial and topoff pumps
            initial_pump = 0
            top_off = 0
            
            print(f"\n=== Processing Trial {trial['trial']} ===")
            print(f"used_topoff flag: {trial.get('used_topoff', False)}")
            print(f"pump_sessions_detail: {trial.get('pump_sessions_detail', 'None')}")
            
            if 'pump_sessions_detail' in trial and trial['pump_sessions_detail'] != '[]':
                try:
                    import ast
                    sessions = ast.literal_eval(trial['pump_sessions_detail'])
                    
                    print(f"Successfully parsed {len(sessions)} sessions:")
                    for i, session in enumerate(sessions):
                        session_topoff = session.get('was_topoff', False)
                        session_pumps = session.get('pumps_selected_this_session', 0)
                        print(f"  Session {i+1}: was_topoff={session_topoff}, pumps={session_pumps}")
                        
                        if session_topoff:
                            top_off = session_pumps
                            print(f"    -> Found TOP-OFF session with {top_off} pumps")
                        else:
                            initial_pump = session_pumps
                            print(f"    -> Found INITIAL session with {initial_pump} pumps")
                            
                except Exception as e:
                    print(f"ERROR parsing sessions: {e}")
                    # Fallback: use total pumps as initial if can't parse sessions
                    initial_pump = trial.get('total_pumps_final', 0)
                    top_off = 0
                    print(f"Using fallback: initial_pump={initial_pump}, top_off=0")
            else:
                # No sessions recorded, use total pumps as initial
                initial_pump = trial.get('total_pumps_final', 0)
                top_off = 0
                print(f"No sessions found, using total_pumps_final={initial_pump}")
            
            # Validation check
            if trial.get('used_topoff', False) and top_off == 0:
                print(f"⚠️  WARNING: Trial {trial['trial']} has used_topoff=True but extracted top_off=0")
            
            row = {
                'Timestamp': trial.get('timestamp', ''),
                'ID': trial.get('participant_id', ''),
                'Treatment': trial.get('treatment', ''),
                'Trial': trial.get('trial', 0),
                'Explosion Point': trial.get('explosion_point', 0),
                'Initial Pump': initial_pump,
                'Top Off': top_off
            }
            
            print(f"Final CSV row: Initial={initial_pump}, TopOff={top_off}")
            simplified_data.append(row)
        
        # Write simplified data
        try:
            with open(filepath, 'w', newline='') as csvfile:
                if simplified_data:
                    fieldnames = ['Timestamp', 'ID', 'Treatment', 'Trial', 'Explosion Point', 'Initial Pump', 'Top Off']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(simplified_data)
            
            print(f"\n✅ Simplified data saved to: {filepath}")
        except Exception as e:
            print(f"❌ Error saving data: {e}")
    
    def quit_experiment(self):
        """Quit the experiment early"""
        if self.trial_data:  # Save if there's any data
            self.save_data()
        self.win.close()
        core.quit()
    
    def run(self):
        """Run the complete BART experiment"""
        try:
            self.show_instructions()
            self.start_new_balloon()
            self.run_trial_loop()
        except Exception as e:
            print(f"Error during experiment: {e}")
            self.quit_experiment()

# Main execution
if __name__ == "__main__":
    try:
        bart = BART()
        bart.run()
    except Exception as e:
        print(f"Error initializing BART: {e}")
        core.quit()