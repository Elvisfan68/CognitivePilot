from psychopy import visual, core, event, data, gui
import random
import numpy as np
import os
from datetime import datetime
import csv
import colorsys
import pygame

class BART:
    def __init__(self):
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
        # Get participant info
        self.get_participant_info()
        
        # Set up color names first
        self.color_names = ['color1', 'color2', 'color3']
        
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

        # Generate distinct random colors
        self.balloon_colors = self.generate_random_colors_hsv(3)
        
        # Point values per pump (in dollars)
        point_values = [0.005, 0.01, 0.05]  # 0.5 cents, 1.0 cents, 5.0 cents
        random.shuffle(point_values)  # Randomize which color gets which value
        
        # Create balloon types with generated colors and point values
        self.balloon_types = {}
        
        for i, label in enumerate(self.color_names):
            self.balloon_types[label] = {
                'points_per_pump': point_values[i],
                'fill_color': self.balloon_colors[i]['fill'],
                'line_color': self.balloon_colors[i]['line'],
                'rgb_values': self.balloon_colors[i]['rgb'],
                'hsv_values': self.balloon_colors[i]['hsv']
            }
        
        # All balloons use the same array size and break point distribution
        self.array_size = 128
        self.break_points = self.generate_break_points()
        
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
        
        # Trial sequence - 45 balloons total (15 of each color)
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
            
        # Print the randomized mapping
        print(f"\nRandomized point values for participant {self.participant_id}:")
        for label, params in self.balloon_types.items():
            value_label = "HIGH" if params['points_per_pump'] == 0.05 else "MEDIUM" if params['points_per_pump'] == 0.01 else "LOW"
            rgb = params['rgb_values']
            hsv = params['hsv_values']
            print(f"{label.upper()}: RGB{rgb} HSV({hsv[0]:.0f}°, {hsv[1]:.2f}, {hsv[2]:.2f}) - {params['points_per_pump']*100:.1f} cents per pump ({value_label})")
    
    def get_participant_info(self):
        """Get participant information"""
        try:
            dlg = gui.Dlg(title="BART - Participant Info")
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
        
    def generate_random_colors_hsv(self, num_colors):
        """Generate colors using HSV for better perceptual separation"""
        colors = []
        
        # For 3 colors, space them 120 degrees apart in hue
        hue_step = 360 / num_colors
        base_hue = random.uniform(0, 360)  # Random starting point
        
        for i in range(num_colors):
            # Evenly spaced hues with random offset
            hue = (base_hue + i * hue_step + random.uniform(-30, 30)) % 360
            
            # Random but reasonable saturation and value
            saturation = random.uniform(0.6, 1.0)  # Avoid pale colors
            value = random.uniform(0.7, 1.0)       # Avoid dark colors
            
            # Convert HSV to RGB
            rgb = list(colorsys.hsv_to_rgb(hue/360, saturation, value))
            
            # Create darker outline
            outline_rgb = [max(0, c-0.3) for c in rgb]
            
            colors.append({
                'fill': rgb,
                'line': outline_rgb,
                'rgb': tuple(int(c*255) for c in rgb),
                'hsv': (hue, saturation, value)
            })
        
        return colors

    def generate_break_points(self):
        """Generate break point sequences - same for all colors since all use same array"""
        print(f"\nGenerating break points for array size {self.array_size}")
        
        # Generate 45 break points total with average of 64
        break_point_sequence = self.generate_sequence_with_exact_average(self.array_size, 64, 45)
        
        # Verify average
        actual_avg = np.mean(break_point_sequence)
        print(f"Generated {len(break_point_sequence)} break points with average: {actual_avg:.3f}")
        print(f"Break points: {break_point_sequence}")
        
        return break_point_sequence

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
        """Create the trial sequence: 45 balloons total (15 of each color), randomized"""
        sequence = []
        
        # Create 15 trials for each color (45 total)
        colors = self.color_names * 15  # Each color appears 15 times
        random.shuffle(colors)  # Randomize the order
        
        # Assign break points
        for i, color in enumerate(colors):
            sequence.append({
                'trial': i + 1,
                'color': color,
                'explosion_point': self.break_points[i]  # Use sequential break points
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

    def setup_display(self):
        """Setup all display elements with scaled text and properly spaced buttons"""
        screen_width = self.win.size[0]
        screen_height = self.win.size[1]
        scale_factor = (screen_height / 1080.0) * 1.5
        
        pump_button_width = int(180 * scale_factor)
        pump_button_height = int(70 * scale_factor)
        collect_button_width = int(240 * scale_factor)
        collect_button_height = int(70 * scale_factor)
        
        pump_button_x = -screen_width // 4
        collect_button_x = screen_width // 4
        button_y = -screen_height // 6
        
        # Balloon
        self.balloon = visual.Circle(
            self.win,
            radius=50,
            pos=[0, 50],
            fillColor='blue',
            lineColor='darkblue',
            lineWidth=2
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
            self.win,
            text='Total Earned: $0.00',
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
            text='Balloon 1 of 45',
            pos=[0, status_y],
            color='black',
            height=self.text_sizes['medium'],
            bold=True
        )
        
        # Instructions below buttons
        self.instruction_text = visual.TextStim(
            self.win,
            text='',
            pos=[0, button_y - 100],
            color='black',
            height=self.text_sizes['normal'],
            wrapWidth=screen_width * 0.8
        )

    def show_instructions(self):
        """Show task instructions with larger text"""
        instructions = [
            "Welcome to the Balloon Analogue Risk Task (BART)\n\n" +
            "In this task, you will pump up balloons to earn money.\n\n" +
            "Press SPACE to continue...",
            
            "Each pump earns you money, but the amount depends on the balloon color.\n\n" +
            "The money goes into a temporary bank that you can collect at any time.\n\n" +
            "Press SPACE to continue...",
            
            "BUT BE CAREFUL!\n\n" +
            "If you pump too much, the balloon will pop and you'll lose\n" +
            "all the money in your temporary bank for that balloon.\n\n" +
            "Press SPACE to continue...",
            
            "Each balloon can pop as early as the first pump or as late as\n" +
            "when it fills the entire screen.\n\n" +
            "You will complete 45 balloons total.\n\n" +
            "Different colored balloons are worth different amounts per pump!\n\n" +
            "Press SPACE to continue...",
            
            "To pump: Click the red PUMP button or press SPACEBAR\n" +
            "To collect money: Click the green 'Collect $$$' button\n\n" +
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
        if self.current_trial >= 45:
            self.end_experiment()
            return
        
        trial_info = self.trial_sequence[self.current_trial]
        
        # Reset balloon state
        self.current_pumps = 0
        self.current_balloon_size = 50
        self.temporary_bank = 0.0
        self.balloon_exploded = False
        
        # Set balloon color
        color_info = self.balloon_types[trial_info['color']]
        self.balloon.fillColor = color_info['fill_color']
        self.balloon.lineColor = color_info['line_color']
        self.balloon.radius = self.current_balloon_size
        
        # Update displays
        self.update_displays()
    
    def pump_balloon(self):
        """Pump the balloon once"""
        if self.current_trial >= 45:
            return
            
        trial_info = self.trial_sequence[self.current_trial]
        explosion_point = trial_info['explosion_point']
        
        # Print info for first pump (debugging)
        if self.current_pumps == 0:
            color_info = self.balloon_types[trial_info['color']]
            print(f"\nBalloon {self.current_trial + 1} ({trial_info['color']}):")
            print(f"Array size: {self.array_size}")
            print(f"Explosion point: {explosion_point}")
            print(f"Points per pump: {color_info['points_per_pump']} (${color_info['points_per_pump']:.3f})")
        
        self.current_pumps += 1
        
        # Check if balloon pops
        if self.current_pumps >= explosion_point:
            self.balloon_pop()
        else:
            # Successful pump
            self.play_sound("pump.mp3")
            
            # Increase balloon size
            self.current_balloon_size += 8
            self.balloon.radius = self.current_balloon_size
            
            # Add money to temporary bank based on balloon color
            color_info = self.balloon_types[trial_info['color']]
            self.temporary_bank += color_info['points_per_pump']
            
            # Update display
            self.update_displays()
    
    def balloon_pop(self):
        """Handle balloon explosion"""
        self.balloon_exploded = True
        self.play_sound("pop.mp3")
        
        # Show explosion effect
        self.show_explosion()
        
        # Record trial data
        self.record_trial_data(exploded=True)
        
        # Reset temporary bank
        self.last_balloon_earned = 0.0
        self.temporary_bank = 0.0
        
        # Move to next trial
        self.current_trial += 1
        core.wait(1.0)
        self.start_new_balloon()
    
    def collect_money(self):
        """Collect money from temporary bank"""
        if self.temporary_bank > 0:
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

    def show_explosion(self):
        """Show balloon explosion animation with scaled text"""
        explosion = visual.Circle(
            self.win,
            radius=self.current_balloon_size * 1.5,
            pos=[0, 50],
            fillColor='red',
            lineColor='darkred'
        )
        
        pop_text = visual.TextStim(
            self.win,
            text='POP!',
            pos=[0, 50],
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
        """Record data for current trial"""
        trial_info = self.trial_sequence[self.current_trial]
        color_info = self.balloon_types[trial_info['color']]
        
        # Determine value level
        if color_info['points_per_pump'] == 0.005:
            value_level = 'low'
        elif color_info['points_per_pump'] == 0.01:
            value_level = 'medium'
        else:  # 0.05
            value_level = 'high'
        
        data_row = {
            'participant_id': self.participant_id,
            'treatment': self.treatment,
            'trial': self.current_trial + 1,
            'balloon_color': trial_info['color'],
            'value_level': value_level,
            'points_per_pump': color_info['points_per_pump'],
            'explosion_point': trial_info['explosion_point'],
            'pumps': self.current_pumps,
            'exploded': exploded,
            'earned_this_balloon': 0.0 if exploded else self.temporary_bank,
            'total_earned': self.total_earned,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.trial_data.append(data_row)

    def update_displays(self):
        """Update all display texts with scaled sizes"""
        self.total_earned_text.text = f'Total Earned: ${self.total_earned:.2f}'
        self.total_earned_text.height = self.text_sizes['medium']
        
        self.last_balloon_text.text = f'Last Balloon: ${self.last_balloon_earned:.2f}'
        self.last_balloon_text.height = self.text_sizes['medium']
        
        self.trial_number_text.text = f'Balloon {self.current_trial + 1} of 45'
        self.trial_number_text.height = self.text_sizes['medium']
        
        if self.temporary_bank > 0:
            self.instruction_text.text = f'Temporary Bank: ${self.temporary_bank:.2f}\nPumps: {self.current_pumps}'
        else:
            self.instruction_text.text = f'Pumps: {self.current_pumps}'
        self.instruction_text.height = self.text_sizes['normal']
        
        self.collect_text.height = self.text_sizes['button']
        self.pump_button_text.height = self.text_sizes['button']
        
    def draw_balloon(self):
        """Draw the balloon"""
        if not self.balloon_exploded:
            self.balloon.draw()
    
    def draw_ui(self):
        """Draw all UI elements"""
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
        """Handle mouse clicks on buttons with better bounds checking"""
        mouse_x, mouse_y = pos
        
        # Check pump button
        pump = self.pump_button_info
        if (pump['x'] - pump['width']//2 < mouse_x < pump['x'] + pump['width']//2 and
            pump['y'] - pump['height']//2 < mouse_y < pump['y'] + pump['height']//2):
            print("Pump button clicked!")
            self.pump_balloon()
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
        clock = core.Clock()
        mouse_pressed = False
        
        while self.current_trial < 45:
            # Handle events
            mouse = event.Mouse()
            keys = event.getKeys(keyList=['space', 'escape'])
            
            # Handle keyboard input
            if keys:
                if 'escape' in keys:
                    self.quit_experiment()
                elif 'space' in keys:
                    self.pump_balloon()
            
            # Handle mouse clicks
            mouse_buttons = mouse.getPressed()
            if mouse_buttons[0] and not mouse_pressed:
                mouse_pressed = True
                pos = mouse.getPos()
                self.handle_mouse_click(pos)
            elif not mouse_buttons[0]:
                mouse_pressed = False
            
            # Draw everything
            self.draw_balloon()
            self.draw_ui()
            self.win.flip()
            
            # Small delay to prevent excessive CPU usage
            core.wait(0.01)
    
    def end_experiment(self):
        """End the experiment and show results"""
        # Calculate final statistics
        # For primary measure, use all collected balloons (not just one value level)
        collected_balloons = [trial for trial in self.trial_data if not trial['exploded']]
        
        if collected_balloons:
            adjusted_pumps = np.mean([trial['pumps'] for trial in collected_balloons])
        else:
            adjusted_pumps = 0
        
        # Show final results
        results_text = f"""Experiment Complete!
        
    Total Earned: ${self.total_earned:.2f}
    Total Balloons: 45
    Balloons Exploded: {sum(1 for trial in self.trial_data if trial['exploded'])}
    Balloons Collected: {sum(1 for trial in self.trial_data if not trial['exploded'])}

    Adjusted Average Pumps: {adjusted_pumps:.2f} pumps

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
        filename = f"BART_data_{self.participant_id}_{self.treatment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Create data directory if it doesn't exist
        if not os.path.exists('Bart Data'):
            os.makedirs('Bart Data')
        
        filepath = os.path.join('Bart Data', filename)
        
        # Write data
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
        
        # Save comprehensive summary
        self.save_comprehensive_summary()
    
    def save_comprehensive_summary(self):
        """Save comprehensive summary for all balloon value levels"""
        try:
            summary_filename = f"BART_summary_{self.participant_id}_{self.treatment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            summary_filepath = os.path.join('Bart Data', summary_filename)
            
            # Identify which color corresponds to which value level
            low_value_color = None
            medium_value_color = None
            high_value_color = None
            
            for color_label, params in self.balloon_types.items():
                if params['points_per_pump'] == 0.005:
                    low_value_color = color_label
                elif params['points_per_pump'] == 0.01:
                    medium_value_color = color_label
                elif params['points_per_pump'] == 0.05:
                    high_value_color = color_label
            
            # Separate data by value level
            low_value_balloons = [trial for trial in self.trial_data if trial['balloon_color'] == low_value_color]
            medium_value_balloons = [trial for trial in self.trial_data if trial['balloon_color'] == medium_value_color]
            high_value_balloons = [trial for trial in self.trial_data if trial['balloon_color'] == high_value_color]
            
            # Non-exploded balloons for adjusted averages
            low_value_collected = [trial for trial in low_value_balloons if not trial['exploded']]
            medium_value_collected = [trial for trial in medium_value_balloons if not trial['exploded']]
            high_value_collected = [trial for trial in high_value_balloons if not trial['exploded']]
            
            # Overall collected balloons
            all_collected = [trial for trial in self.trial_data if not trial['exploded']]
            
            with open(summary_filepath, 'w', encoding='utf-8') as f:
                f.write(f"BART Comprehensive Summary Report\n")
                f.write(f"Participant ID: {self.participant_id}\n")
                f.write(f"Treatment: {self.treatment}\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write(f"TASK DESIGN:\n")
                f.write(f"Total Balloons: 45 (15 of each value level)\n")
                f.write(f"All balloons use same array size: {self.array_size}\n")
                f.write(f"Break points average: 64 (range 1-{self.array_size})\n\n")
                
                f.write(f"RANDOMIZED COLOR-VALUE MAPPING:\n")
                f.write(f"Low Value (0.5¢/pump): {low_value_color.upper()} - RGB{self.balloon_types[low_value_color]['rgb_values']}\n")
                f.write(f"Medium Value (1.0¢/pump): {medium_value_color.upper()} - RGB{self.balloon_types[medium_value_color]['rgb_values']}\n")
                f.write(f"High Value (5.0¢/pump): {high_value_color.upper()} - RGB{self.balloon_types[high_value_color]['rgb_values']}\n\n")
                
                f.write(f"OVERALL PERFORMANCE:\n")
                f.write(f"Total Earned: ${self.total_earned:.2f}\n")
                f.write(f"Total Explosions: {sum(1 for trial in self.trial_data if trial['exploded'])}\n")
                f.write(f"Total Collections: {sum(1 for trial in self.trial_data if not trial['exploded'])}\n")
                
                # PRIMARY MEASURE (All collected balloons)
                if all_collected:
                    primary_measure = np.mean([trial['pumps'] for trial in all_collected])
                    f.write(f"\n*** PRIMARY MEASURE: ADJUSTED AVERAGE PUMPS = {primary_measure:.2f} ***\n")
                    f.write(f"(Based on {len(all_collected)} collected balloons out of 45 total)\n")
                else:
                    f.write(f"\n*** PRIMARY MEASURE: ADJUSTED AVERAGE PUMPS = 0.00 ***\n")
                    f.write(f"(No balloons collected)\n")
                
                # BREAKDOWN BY VALUE LEVEL
                f.write(f"\n=== BREAKDOWN BY VALUE LEVEL ===\n")
                
                f.write(f"\nLOW VALUE BALLOONS (0.5¢/pump - {low_value_color.upper()}):\n")
                f.write(f"  Total Trials: {len(low_value_balloons)}\n")
                f.write(f"  Exploded: {len([t for t in low_value_balloons if t['exploded']])}\n")
                f.write(f"  Collected: {len(low_value_collected)}\n")
                if low_value_collected:
                    f.write(f"  Adjusted Average Pumps: {np.mean([t['pumps'] for t in low_value_collected]):.2f}\n")
                    f.write(f"  Total Earned: ${sum([t['earned_this_balloon'] for t in low_value_collected]):.2f}\n")
                
                f.write(f"\nMEDIUM VALUE BALLOONS (1.0¢/pump - {medium_value_color.upper()}):\n")
                f.write(f"  Total Trials: {len(medium_value_balloons)}\n")
                f.write(f"  Exploded: {len([t for t in medium_value_balloons if t['exploded']])}\n")
                f.write(f"  Collected: {len(medium_value_collected)}\n")
                if medium_value_collected:
                    f.write(f"  Adjusted Average Pumps: {np.mean([t['pumps'] for t in medium_value_collected]):.2f}\n")
                    f.write(f"  Total Earned: ${sum([t['earned_this_balloon'] for t in medium_value_collected]):.2f}\n")
                
                f.write(f"\nHIGH VALUE BALLOONS (5.0¢/pump - {high_value_color.upper()}):\n")
                f.write(f"  Total Trials: {len(high_value_balloons)}\n")
                f.write(f"  Exploded: {len([t for t in high_value_balloons if t['exploded']])}\n")
                f.write(f"  Collected: {len(high_value_collected)}\n")
                if high_value_collected:
                    f.write(f"  Adjusted Average Pumps: {np.mean([t['pumps'] for t in high_value_collected]):.2f}\n")
                    f.write(f"  Total Earned: ${sum([t['earned_this_balloon'] for t in high_value_collected]):.2f}\n")
                
                # VALUE SENSITIVITY ANALYSIS
                f.write(f"\n=== VALUE SENSITIVITY ANALYSIS ===\n")
                if low_value_collected and medium_value_collected and high_value_collected:
                    low_avg = np.mean([t['pumps'] for t in low_value_collected])
                    med_avg = np.mean([t['pumps'] for t in medium_value_collected])
                    high_avg = np.mean([t['pumps'] for t in high_value_collected])
                    
                    f.write(f"Expected pattern: Low Value < Medium Value < High Value\n")
                    f.write(f"Observed pattern: {low_avg:.1f} < {med_avg:.1f} < {high_avg:.1f}\n")
                    
                    if low_avg < med_avg < high_avg:
                        f.write(f"✓ VALID: Participant showed expected value sensitivity\n")
                    else:
                        f.write(f"⚠ WARNING: Participant may not have shown expected value sensitivity\n")
                        
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