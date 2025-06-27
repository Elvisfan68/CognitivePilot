from psychopy import visual, core, event, data, gui
import random
import numpy as np
import os
from datetime import datetime
import csv
import colorsys
import pygame
import math

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
            color=[0.8, 0.8, 0.8],
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
        
        # Wheel control variables
        self.selected_pumps = 1
        self.wheel_angle = 0
        self.wheel_dragging = False
        self.last_mouse_angle = 0
        
        # Pumping animation variables
        self.is_pumping = False
        self.pumps_to_simulate = 0
        self.pumps_simulated = 0
        self.pump_timer = 0
        self.pump_interval = 0.1  # Time between simulated pumps
        
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
        
        # Trial sequence - 30 balloons total
        self.trial_sequence = self.create_trial_sequence()

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
            'button': int(24 * scale_factor),
            'huge': int(50 * scale_factor)
        }
        
        print(f"Screen size: {screen_width}x{screen_height}")
        print(f"Scale factor: {scale_factor:.2f}")
        print(f"Text sizes: {self.text_sizes}")

    def update_wheel_indicator(self):
        """Update wheel indicator position and pump count"""
        # Calculate visual angle for indicator (always show current position mod 2π)
        visual_angle = self.wheel_angle % (2 * math.pi)
        
        # Calculate indicator position
        indicator_x = self.wheel_center[0] + (self.wheel_radius - 20) * math.cos(visual_angle)
        indicator_y = self.wheel_center[1] + (self.wheel_radius - 20) * math.sin(visual_angle)
        
        self.wheel_indicator.pos = [indicator_x, indicator_y]
        
        # Update pump count text
        self.pump_count_text.text = f'Pumps: {self.selected_pumps}'

    def setup_display(self):
        """Setup all display elements with wheel control"""
        screen_width = self.win.size[0]
        screen_height = self.win.size[1]
        scale_factor = (screen_height / 1080.0) * 1.5
        
        # Button dimensions
        pump_button_width = int(200 * scale_factor)
        pump_button_height = int(70 * scale_factor)
        collect_button_width = int(240 * scale_factor)
        collect_button_height = int(70 * scale_factor)
        
        # Better spacing - move buttons further down
        pump_button_x = -screen_width // 5
        collect_button_x = screen_width // 5
        button_y = -screen_height // 3
        
        # Wheel control (positioned well above buttons)
        wheel_y = button_y + int(200 * scale_factor)
        wheel_radius = int(60 * scale_factor)  # Smaller wheel
        
        # Balloon (move up more)
        self.balloon = visual.Circle(
            self.win,
            radius=50,
            pos=[0, int(150 * scale_factor)],  # Higher position
            fillColor='blue',
            lineColor='darkblue',
            lineWidth=2
        )
        
        # Wheel control elements
        self.wheel_center = (0, wheel_y)
        self.wheel_radius = wheel_radius
        
        # Wheel background circle
        self.wheel_background = visual.Circle(
            self.win,
            radius=wheel_radius,
            pos=self.wheel_center,
            fillColor='lightgray',
            lineColor='black',
            lineWidth=3
        )
        
        # Wheel indicator (pointer)
        self.wheel_indicator = visual.Circle(
            self.win,
            radius=8,
            pos=[self.wheel_center[0] + wheel_radius - 15, self.wheel_center[1]],
            fillColor='red',
            lineColor='darkred',
            lineWidth=2
        )
        
        # Pump count display (closer to wheel)
        self.pump_count_text = visual.TextStim(
            self.win,
            text='Pumps: 1',
            pos=[0, wheel_y - wheel_radius - int(30 * scale_factor)],
            color='black',
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
            color='black',
            height=self.text_sizes['medium'],
            bold=True
        )
        
        self.last_balloon_text = visual.TextStim(
            self.win,
            text='Last Balloon: $0.00',
            pos=[screen_width // 3, status_y],
            color='black',
            height=self.text_sizes['medium'],
            bold=True
        )
        
        self.trial_number_text = visual.TextStim(
            self.win,
            text='Balloon 1 of 30',
            pos=[0, status_y],
            color='black',
            height=self.text_sizes['medium'],
            bold=True
        )
        
        # Instructions below buttons (more space)
        # Instructions below buttons (move higher up)
        self.instruction_text = visual.TextStim(
            self.win,
            text='',
            pos=[0, button_y - int(80 * scale_factor)],  # Reduced from 120 to 80
            color='black',
            height=self.text_sizes['normal'],
            wrapWidth=screen_width * 0.9  # Increased wrap width
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
            
            "IMPORTANT: Research shows that 64 pumps provides\n" +
            "optimal performance on this task.\n\n" +
            "You will complete 30 balloons total.\n\n" +
            "Press SPACE to continue...",
            
            "CONTROLS:\n\n" +
            "• Drag the wheel to select number of pumps (1-128)\n" +
            "• One full rotation ≈ 30 pumps\n" +
            "• Click PUMP to pump that many times\n" +
            "• You can pump multiple times per balloon\n" +
            "• Click 'Collect $$$' to collect and move to next balloon\n\n" +
            "Try to earn as much money as possible!\n\n" +
            "Press SPACE to begin..."
        ]
        
        instruction_display = visual.TextStim(
            self.win,
            text='',
            pos=[0, 0],
            color='black',
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
        
        # Reset session tracking
        self.pump_sessions = []
        self.session_number = 0
        
        # Reset balloon appearance
        self.balloon.fillColor = 'blue'
        self.balloon.lineColor = 'darkblue'
        self.balloon.radius = self.current_balloon_size
        
        # Reset wheel to 1
        self.selected_pumps = 1
        self.wheel_angle = 0
        self.update_wheel_position()
        
        # Update displays
        self.update_displays()

    def update_wheel_position(self):
        """Update wheel indicator position based on selected pumps"""
        # Convert pumps (1-128) to angle
        # Since one rotation = ~30 pumps, we need multiple rotations for the full range
        total_angle_range = (127 / 30) * 2 * math.pi  # ~26.8 radians for full range
        pump_ratio = (self.selected_pumps - 1) / 127
        self.wheel_angle = pump_ratio * total_angle_range
        
        # Calculate visual indicator position (mod 2π for display)
        visual_angle = self.wheel_angle % (2 * math.pi)
        indicator_x = self.wheel_center[0] + (self.wheel_radius - 20) * math.cos(visual_angle)
        indicator_y = self.wheel_center[1] + (self.wheel_radius - 20) * math.sin(visual_angle)
        
        self.wheel_indicator.pos = [indicator_x, indicator_y]

    def handle_wheel_interaction(self, mouse_pos, mouse_pressed):
        """Handle wheel interaction for selecting pump count"""
        if self.is_pumping:  # Don't allow wheel interaction during pumping
            return
            
        mouse_x, mouse_y = mouse_pos
        
        # Check if mouse is over wheel
        wheel_x, wheel_y = self.wheel_center
        distance = math.sqrt((mouse_x - wheel_x)**2 + (mouse_y - wheel_y)**2)
        
        if distance <= self.wheel_radius:
            if mouse_pressed and not self.wheel_dragging:
                self.wheel_dragging = True
                # Calculate initial angle
                self.last_mouse_angle = math.atan2(mouse_y - wheel_y, mouse_x - wheel_x)
                
            elif self.wheel_dragging:
                # Calculate current angle
                current_angle = math.atan2(mouse_y - wheel_y, mouse_x - wheel_x)
                
                # Calculate angle difference
                angle_diff = current_angle - self.last_mouse_angle
                
                # Handle angle wrapping
                if angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                elif angle_diff < -math.pi:
                    angle_diff += 2 * math.pi
                
                # SMOOTHER ROTATION: More sensitive to mouse movement
                scaled_angle_diff = angle_diff
                
                # Update wheel angle (allow multiple rotations)
                self.wheel_angle += scaled_angle_diff
                
                # Convert angle to pump count: 
                # One full rotation (2π radians) = ~30 pumps
                # So we need 4.27 rotations to get from 1 to 128 pumps
                # Total angle range = 4.27 * 2π = 26.8 radians for full 1-128 range
                total_angle_range = (127 / 30) * 2 * math.pi  # ~26.8 radians
                
                # Convert current angle to pump count (1-128)
                pump_ratio = (self.wheel_angle % total_angle_range) / total_angle_range
                new_pumps = max(1, min(128, int(1 + pump_ratio * 127)))
                
                # Only update if the value actually changed (reduces jitter)
                if new_pumps != self.selected_pumps:
                    self.selected_pumps = new_pumps
                    # Update indicator and display
                    self.update_wheel_indicator()
                
                self.last_mouse_angle = current_angle
        
        if not mouse_pressed:
            self.wheel_dragging = False

    def start_pump_simulation(self):
        """Start the automatic pumping simulation - ADDS to existing pumps"""
        if self.is_pumping:
            return
            
        # ADD pumps to existing total, don't replace
        self.is_pumping = True
        self.pumps_to_simulate = self.selected_pumps  # This is the NEW pumps to add
        self.pumps_simulated = 0  # Reset the simulation counter for this session
        self.pump_timer = core.getTime()
        
        print(f"Adding {self.pumps_to_simulate} more pumps. Current total: {self.current_pumps}")
    def update_pump_simulation(self):
        """Update the pumping simulation"""
        if not self.is_pumping:
            return False
            
        # Use PsychoPy's getTime() method
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
                
                # Record this pump session
                self.record_pump_session()
                
                # NO AUTO-COLLECT: Just stop pumping, let user decide
                return False
        
        return True

    def record_pump_session(self):
        """Record data for this pump session"""
        trial_info = self.trial_sequence[self.current_trial]
        
        self.session_number += 1
        
        session_data = {
            'participant_id': self.participant_id,
            'treatment': self.treatment,
            'trial': self.current_trial + 1,
            'session': self.session_number,
            'explosion_point': trial_info['explosion_point'],
            'pumps_selected_this_session': self.selected_pumps,
            'pumps_actual_this_session': self.pumps_simulated,
            'total_pumps_so_far': self.current_pumps,
            'temporary_bank': self.temporary_bank,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.pump_sessions.append(session_data)
        print(f"Session {self.session_number}: Selected {self.selected_pumps}, Total pumps now: {self.current_pumps}")

    def collect_money(self):
        """Collect money from temporary bank"""
        if self.temporary_bank > 0 and not self.is_pumping:
            # Track last balloon info BEFORE any changes
            self.last_balloon_pumps = self.current_pumps
            self.last_balloon_exploded = False
            print(f"DEBUG: Collecting - tracking {self.current_pumps} pumps")  # Debug line
            
            # Play collection sound and animate money transfer
            self.animate_money_collection()
            
            # Transfer money
            self.last_balloon_earned = self.temporary_bank
            self.total_earned += self.temporary_bank
            
            # Record trial data with all pump sessions
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
        
        # Track last balloon info BEFORE any changes
        self.last_balloon_pumps = self.current_pumps
        self.last_balloon_exploded = True
        self.last_balloon_earned = 0.0
        print(f"DEBUG: Exploding - tracking {self.current_pumps} pumps")  # Debug line
        
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
            'pump_sessions_detail': str(self.pump_sessions),  # Store all sessions as string
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.trial_data.append(data_row)

    def update_displays(self):
        """Update all display texts"""
        self.total_earned_text.text = f'Total Earned: ${self.total_earned:.2f}'
        
        # Enhanced last balloon display - only show explosion point if it actually popped
        if self.current_trial > 0:  # Only show if we've completed at least one balloon
            if self.last_balloon_exploded:
                trial_info = self.trial_sequence[self.current_trial - 1]  # Get previous trial info
                explosion_point = trial_info['explosion_point']
                self.last_balloon_text.text = f'Last: ${self.last_balloon_earned:.2f}\nYou pumped: {self.last_balloon_pumps}\nPopped at: {explosion_point}'
            else:
                self.last_balloon_text.text = f'Last: ${self.last_balloon_earned:.2f}\nYou pumped: {self.last_balloon_pumps}'
        else:
            self.last_balloon_text.text = 'Last Balloon: $0.00'
        
        self.trial_number_text.text = f'Balloon {self.current_trial + 1} of {self.total_trials}'
        
        # Update pump count display - show what you're ADDING
        self.pump_count_text.text = f'Pumps: {self.selected_pumps}'
        
        if self.is_pumping:
            self.instruction_text.text = f'Pumping {self.pumps_simulated}/{self.pumps_to_simulate}\nTotal: {self.current_pumps}'
        elif self.current_pumps > 0:
            self.instruction_text.text = f'Total: {self.current_pumps}\nBank: ${self.temporary_bank:.2f}\nADD more or COLLECT'
        else:
            self.instruction_text.text = f'Select pumps, then PUMP'
       

    def draw_balloon(self):
        """Draw the balloon"""
        if not self.balloon_exploded:
            self.balloon.draw()
    
    def draw_ui(self):
        """Draw all UI elements"""
        # Draw wheel control
        self.wheel_background.draw()
        self.wheel_indicator.draw()
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
        if self.is_pumping:  # Don't allow button clicks during pumping
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
            
            # Handle wheel interaction (always check for dragging)
            self.handle_wheel_interaction(mouse_pos, current_mouse_pressed)
            
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
        """End the experiment and show results with automatic BART statistics"""
        # Calculate comprehensive statistics as per automatic BART research
        
        # Primary measure: Total pumps (mean across all trials)
        all_pumps = [trial['total_pumps_final'] for trial in self.trial_data]
        mean_total_pumps = np.mean(all_pumps) if all_pumps else 0
        
        # Block analysis (trials 1-10, 11-20, 21-30)
        block1_pumps = [trial['total_pumps_final'] for trial in self.trial_data[0:10]]
        block2_pumps = [trial['total_pumps_final'] for trial in self.trial_data[10:20]]
        block3_pumps = [trial['total_pumps_final'] for trial in self.trial_data[20:30]]
        
        mean_block1 = np.mean(block1_pumps) if block1_pumps else 0
        mean_block2 = np.mean(block2_pumps) if block2_pumps else 0
        mean_block3 = np.mean(block3_pumps) if block3_pumps else 0
        
        # Explosion analysis
        total_explosions = sum(1 for trial in self.trial_data if trial['exploded'])
        
        # Money earned by block
        total_money = self.total_earned
        
        # Show final results
        results_text = f"""Experiment Complete!
        
    PRIMARY MEASURE:
    Mean Total Pumps: {mean_total_pumps:.2f}
    
    BLOCK ANALYSIS:
    Block 1 (1-10): {mean_block1:.2f} pumps
    Block 2 (11-20): {mean_block2:.2f} pumps  
    Block 3 (21-30): {mean_block3:.2f} pumps
    
    Total Earned: ${total_money:.2f}
    Total Explosions: {total_explosions}
    
    IMPORTANT: Research shows 64 pumps is optimal.
    
    Thank you for participating!
    
    Press SPACE to exit."""
        
        # Create larger results display
        results_display = visual.TextStim(
            self.win,
            text=results_text,
            pos=[0, 0],
            color='black',
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
        """Save experimental data to CSV file"""
        filename = f"BART_Manual_data_{self.participant_id}_{self.treatment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Create data directory if it doesn't exist
        if not os.path.exists('Bart Data'):
            os.makedirs('Bart Data')
        
        filepath = os.path.join('Bart Data', filename)
        
        # Write main trial data
        try:
            with open(filepath, 'w', newline='') as csvfile:
                if self.trial_data:
                    fieldnames = self.trial_data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.trial_data)
            
            print(f"Data saved to: {filepath}")
        except Exception as e:
            print(f"Error saving data: {e}")
        
        # Save detailed pump sessions
        self.save_pump_sessions()
        
        # Save comprehensive summary
        self.save_comprehensive_summary()

    def save_pump_sessions(self):
        """Save detailed pump session data"""
        session_filename = f"BART_Sessions_{self.participant_id}_{self.treatment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        session_filepath = os.path.join('Bart Data', session_filename)
        
        try:
            # Collect all pump sessions from all trials
            all_sessions = []
            for trial in self.trial_data:
                if 'pump_sessions_detail' in trial and trial['pump_sessions_detail'] != '[]':
                    # Parse the string representation back to list
                    import ast
                    sessions = ast.literal_eval(trial['pump_sessions_detail'])
                    all_sessions.extend(sessions)
            
            if all_sessions:
                with open(session_filepath, 'w', newline='') as csvfile:
                    fieldnames = all_sessions[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_sessions)
                
                print(f"Pump sessions saved to: {session_filepath}")
        except Exception as e:
            print(f"Error saving pump sessions: {e}")
    
    def save_comprehensive_summary(self):
        """Save comprehensive summary with manual BART statistics"""
        try:
            summary_filename = f"BART_Manual_summary_{self.participant_id}_{self.treatment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            summary_filepath = os.path.join('Bart Data', summary_filename)
            
            # Calculate all statistics
            all_pumps = [trial['total_pumps_final'] for trial in self.trial_data]
            mean_total_pumps = np.mean(all_pumps) if all_pumps else 0
            
            # Block analysis
            block1_pumps = [trial['total_pumps_final'] for trial in self.trial_data[0:10]]
            block2_pumps = [trial['total_pumps_final'] for trial in self.trial_data[10:20]]
            block3_pumps = [trial['total_pumps_final'] for trial in self.trial_data[20:30]]
            
            mean_block1 = np.mean(block1_pumps) if block1_pumps else 0
            mean_block2 = np.mean(block2_pumps) if block2_pumps else 0
            mean_block3 = np.mean(block3_pumps) if block3_pumps else 0
            
            # Session analysis
            total_sessions = sum(trial['total_pump_sessions'] for trial in self.trial_data)
            avg_sessions_per_trial = total_sessions / len(self.trial_data) if self.trial_data else 0
            
            # Explosion analysis
            total_explosions = sum(1 for trial in self.trial_data if trial['exploded'])
            
            with open(summary_filepath, 'w', encoding='utf-8') as f:
                f.write(f"Manual BART Comprehensive Summary Report\n")
                f.write(f"Participant ID: {self.participant_id}\n")
                f.write(f"Treatment: {self.treatment}\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write(f"TASK DESIGN:\n")
                f.write(f"Total Trials: 30 (3 blocks of 10)\n")
                f.write(f"Array size: {self.array_size}\n")
                f.write(f"Break points average: 64 per block\n")
                f.write(f"Points per pump: 1 cent\n")
                f.write(f"Multiple pump sessions allowed per balloon\n")
                f.write(f"Manual collection required\n\n")
                
                f.write(f"=== PRIMARY MEASURES ===\n")
                f.write(f"*** MEAN TOTAL PUMPS: {mean_total_pumps:.2f} *** (PRIMARY DEPENDENT VARIABLE)\n")
                f.write(f"Total Money Earned: ${self.total_earned:.2f}\n")
                f.write(f"Total Explosions: {total_explosions}\n")
                f.write(f"Total Pump Sessions: {total_sessions}\n")
                f.write(f"Average Sessions per Trial: {avg_sessions_per_trial:.2f}\n\n")
                
                f.write(f"=== BLOCK ANALYSIS ===\n")
                f.write(f"Block 1 (Trials 1-10): Mean Pumps = {mean_block1:.2f}\n")
                f.write(f"Block 2 (Trials 11-20): Mean Pumps = {mean_block2:.2f}\n")
                f.write(f"Block 3 (Trials 21-30): Mean Pumps = {mean_block3:.2f}\n\n")
                
                f.write(f"=== LEARNING/ADAPTATION ANALYSIS ===\n")
                if mean_block1 > 0 and mean_block3 > 0:
                    change_over_time = mean_block3 - mean_block1
                    f.write(f"Change from Block 1 to Block 3: {change_over_time:.2f} pumps\n")
                    if change_over_time < 0:
                        f.write(f"Pattern: Decreased risk-taking over time (adaptive learning)\n")
                    elif change_over_time > 0:
                        f.write(f"Pattern: Increased risk-taking over time\n")
                    else:
                        f.write(f"Pattern: Stable risk-taking across blocks\n")
                
                f.write(f"\n=== OPTIMALITY ANALYSIS ===\n")
                f.write(f"Optimal strategy: 64 pumps per balloon\n")
                f.write(f"Participant's mean: {mean_total_pumps:.2f} pumps\n")
                deviation_from_optimal = abs(mean_total_pumps - 64)
                f.write(f"Deviation from optimal: {deviation_from_optimal:.2f} pumps\n")
                        
            print(f"Comprehensive summary saved to: {summary_filepath}")
        except Exception as e:
            print(f"Error saving comprehensive summary: {e}")
    
    def quit_experiment(self):
        """Quit the experiment early"""
        if self.trial_data:  # Only save if there's data
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