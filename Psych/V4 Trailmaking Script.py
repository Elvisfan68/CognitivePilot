from psychopy import visual, event, core, logging, gui
import numpy as np
import csv
import random
import os

# Function to calculate scaling factors based on screen size
def get_scaling_factors(win_size):
    """Calculate scaling factors based on screen size relative to 1920x1080 baseline"""
    baseline_width = 1920
    baseline_height = 1080
    
    width_scale = win_size[0] / baseline_width
    height_scale = win_size[1] / baseline_height
    
    # Use the smaller scale to maintain aspect ratio
    scale_factor = min(width_scale, height_scale)
    
    return scale_factor

# Function to check overlap between circles
def check_overlap(new_pos, existing_positions, radius):
    for (x, y) in existing_positions:
        if np.sqrt((new_pos[0] - x) ** 2 + (new_pos[1] - y) ** 2) < radius * 2:
            return True
    return False

# Function to generate non-overlapping positions
def generate_positions(num_elements, circle_radius, win_size=(1024, 768), max_attempts=1000, reserve_bottom=False):
    positions = []
    attempts = 0
    margin = circle_radius * 2
    
    # Reserve space at bottom if labels will be shown (scale with screen size)
    bottom_margin = int(win_size[1] * 0.3) if reserve_bottom else margin
    
    while len(positions) < num_elements and attempts < max_attempts:
        new_pos = (np.random.randint(-win_size[0]//2 + margin, win_size[0]//2 - margin), 
                   np.random.randint(-win_size[1]//2 + bottom_margin, win_size[1]//2 - margin))
        
        if not check_overlap(new_pos, positions, circle_radius):
            positions.append(new_pos)
        attempts += 1
    
    if len(positions) < num_elements:
        print(f"Warning: Could only generate {len(positions)} positions out of {num_elements}")
    
    return positions

# Function to get shape names
def get_shape_names(count=6):
    shapes = ['triangle', 'square', 'pentagon', 'hexagon', 'heptagon', 'octagon']
    return shapes[:count]

# Function to create a shape stimulus
def create_shape(win, shape_name, pos, size=35, fillColor='white', lineColor='black', scale_factor=1.0):
    """Create actual shape stimuli based on shape name with scaling and rainbow colors"""
    scaled_size = size * scale_factor
    scaled_line_width = max(1, int(2 * scale_factor))
    
    # Define rainbow colors for shapes (in order of increasing sides)
    shape_colors = {
        'triangle': 'red',      # 3 sides
        'square': 'orange',     # 4 sides  
        'pentagon': 'yellow',   # 5 sides
        'hexagon': 'green',     # 6 sides
        'heptagon': 'blue',     # 7 sides
        'octagon': 'indigo',    # 8 sides
        'nonagon': 'purple',    # 9 sides (using purple for indigo)
        'decagon': 'violet'     # 10 sides
    }
    
    # Get the color for this shape, default to white if not found
    shape_color = shape_colors.get(shape_name, fillColor)
    
    if shape_name == 'triangle':
        vertices = []
        for i in range(3):
            angle = i * 2 * np.pi / 3 - np.pi/2  # Start from top
            x = scaled_size * np.cos(angle)
            y = scaled_size * np.sin(angle)
            vertices.append([x, y])
        return visual.ShapeStim(win, vertices=vertices, pos=pos, 
                              fillColor=shape_color, lineColor=lineColor, lineWidth=scaled_line_width)
    
    elif shape_name == 'square':
        return visual.Rect(win, width=scaled_size*1.8, height=scaled_size*1.8, pos=pos,
                          fillColor=shape_color, lineColor=lineColor, lineWidth=scaled_line_width)
    
    elif shape_name in ['pentagon', 'hexagon', 'heptagon', 'octagon', 'nonagon', 'decagon']:
        # Map shape names to number of sides
        sides_map = {
            'pentagon': 5, 'hexagon': 6, 'heptagon': 7, 'octagon': 8,
            'nonagon': 9, 'decagon': 10
        }
        n_sides = sides_map[shape_name]
        
        vertices = []
        for i in range(n_sides):
            angle = i * 2 * np.pi / n_sides - np.pi/2  # Start from top
            x = scaled_size * np.cos(angle)
            y = scaled_size * np.sin(angle)
            vertices.append([x, y])
        
        return visual.ShapeStim(win, vertices=vertices, pos=pos,
                              fillColor=shape_color, lineColor=lineColor, lineWidth=scaled_line_width)
    
    else:
        # Fallback to circle if shape not recognized
        return visual.Circle(win, radius=scaled_size, pos=pos,
                           fillColor=shape_color, lineColor=lineColor, lineWidth=scaled_line_width)
# Function to create trial sequence
def create_trial_sequence(categories, sequence_type, category_order=None):
    """
    Creates a trial sequence based on categories and sequence type
    categories: list of category types ['numbers', 'letters', 'shapes']
    sequence_type: 'ascending' or 'descending'
    category_order: order in which to cycle through categories
    """
    if 'numbers' in categories:
        numbers = list(range(1, 7))  # 1-6
    if 'letters' in categories:
        letters = ['A', 'B', 'C', 'D', 'E', 'F']
    if 'shapes' in categories:
        shapes = get_shape_names(6)
    
    sequence = []
    
    if len(categories) == 1:
        # Single category
        if 'numbers' in categories:
            sequence = numbers if sequence_type == 'ascending' else numbers[::-1]
        elif 'letters' in categories:
            sequence = letters if sequence_type == 'ascending' else letters[::-1]
        elif 'shapes' in categories:
            sequence = shapes if sequence_type == 'ascending' else shapes[::-1]
    else:
        # Multiple categories - create full sequence using ALL items
        # Create lists for each category
        category_items = {}
        if 'numbers' in categories:
            category_items['numbers'] = numbers if sequence_type == 'ascending' else numbers[::-1]
        if 'letters' in categories:
            category_items['letters'] = letters if sequence_type == 'ascending' else letters[::-1]
        if 'shapes' in categories:
            category_items['shapes'] = shapes if sequence_type == 'ascending' else shapes[::-1]
        
        # Create the full sequence by cycling through categories
        # We need 18 items total (6 from each of the 3 categories)
        total_items = 18
        items_per_category = 6
        
        for i in range(total_items):
            cat_index = i % len(category_order)
            category = category_order[cat_index]
            item_index = i // len(category_order)
            
            if item_index < items_per_category:
                sequence.append(category_items[category][item_index])
    
    return sequence

# Function to run a single trial
# Function to run a single trial
def run_trial(win, trial_name, sequence, instructions_text, filename_prefix, master_log_writer, sequence_type=None, category_order=None):
    """Run a single TMT trial with detailed error tracking"""
    
    # Get scaling factors for this screen
    scale_factor = get_scaling_factors(win.size)
    
    # Scale text sizes
    instruction_text_size = int(50 * scale_factor)
    stimulus_text_size = int(28 * scale_factor)
    label_text_size = int(30 * scale_factor)
    feedback_text_size = int(50 * scale_factor)
    
    # Scale other elements
    circle_radius = int(45 * scale_factor)
    shape_size = int(35 * scale_factor)
    line_width = max(1, int(3 * scale_factor))
    
    # Scale wrap width for instructions
    wrap_width = int(1200 * scale_factor)
    
    # Display instructions and visual together (no overlap)
    if (('Experimental' in trial_name and len(sequence) == 18) or ('Mixed' in trial_name and len(sequence) == 18)):
        win.clearBuffer()
        # Draw instructions text higher up
        instructions = visual.TextStim(
            win,
            text=instructions_text,
            height=instruction_text_size,
            wrapWidth=wrap_width,
            pos=(0, 300 * scale_factor),  # Move text up
            color='white'
        )
        instructions.draw()
        # Draw visual rows below (but do NOT flip inside the function)
        draw_instruction_visuals(
            win,
            category_order,
            sequence_type,
            category_order,
            scale_factor,
            y_offset=-250 * scale_factor,  # Lower the visuals
            do_flip=False
        )
        win.flip()
        keys = event.waitKeys()
    else:
        # Default for non-mixed/non-experimental
        instructions = visual.TextStim(win, text=instructions_text, height=instruction_text_size, wrapWidth=wrap_width)
        instructions.draw()
        win.flip()
        keys = event.waitKeys()
    
    # Set up trial parameters
    num_elements = len(sequence)
    
    # Generate positions
    screen_size = win.size
    will_show_labels = sequence_type and category_order and ('Experimental' in trial_name or 'Mixed' in trial_name)
    positions = generate_positions(num_elements, circle_radius, win_size=screen_size, reserve_bottom=will_show_labels)
    
    # Create visual stimuli
    stimuli = []
    background_circles = []  # Background circles for all stimuli
    
    for i in range(num_elements):
        # Create background circle with scaled radius
        bg_circle = visual.Circle(win, radius=circle_radius, pos=positions[i], 
                                fillColor='lightgray', lineColor='black', lineWidth=max(1, int(2 * scale_factor)))
        background_circles.append(bg_circle)
        
        # Create the stimulus based on type
        item = sequence[i]
        
        if isinstance(item, int):  # Number
            stimulus = visual.TextStim(win, text=str(item), pos=positions[i], height=stimulus_text_size, color='black')
        elif isinstance(item, str) and len(item) == 1:  # Letter
            stimulus = visual.TextStim(win, text=item, pos=positions[i], height=stimulus_text_size, color='black')
        else:  # Shape
            stimulus = create_shape(win, item, positions[i], size=shape_size, fillColor='white', lineColor='black', scale_factor=1.0)
        
        stimuli.append(stimulus)
    
    # Create bottom-center labels for experimental trials AND familiarization mixed trials
    corner_labels = []
    if sequence_type and category_order and ('Experimental' in trial_name or 'Mixed' in trial_name):
        # Calculate scaled positions for labels
        label_y_1 = -win.size[1]//2 + int(120 * scale_factor)
        label_y_2 = -win.size[1]//2 + int(80 * scale_factor)
        
        # Order type label - centered at bottom in reserved space
        order_label = visual.TextStim(win, 
                                    text=f"Order: {sequence_type.capitalize()}", 
                                    pos=(0, label_y_1),  # In reserved bottom area
                                    height=label_text_size, color='red', bold=True,
                                    anchorHoriz='center')
        
        # Category order label - centered at bottom in reserved space - FORCE ONE LINE
        category_text = " → ".join(category_order)
        category_label = visual.TextStim(win, 
                                    text=f"Categories: {category_text}", 
                                    pos=(0, label_y_2),  # In reserved bottom area
                                    height=label_text_size, color='red', bold=True,
                                    anchorHoriz='center',
                                    wrapWidth=win.size[0])  # Set wrap width to full screen width
        
        corner_labels = [order_label, category_label]
        print(f"Created {len(corner_labels)} labels")  # Debug print
    
    # Trial execution
    responses = []
    mouse = event.Mouse(win=win)
    clock = core.Clock()
    trial_start_time = core.Clock()
    line_stimuli = []
    total_errors = 0
    
    # Track errors per connection
    wrong_guesses_this_connection = 0
    previous_wrong_circles = set()  # Track which circles were clicked wrong this connection
    
    # Main trial loop
    for target_index in range(num_elements):
        found_target = False
        clock.reset()  # Reset for this connection
        wrong_guesses_this_connection = 0
        previous_wrong_circles.clear()
        
        while not found_target:
            # CHECK FOR ESCAPE KEY DURING TRIAL
            keys = event.getKeys(keyList=['escape'])
            if keys:
                print(f"Escape pressed during {trial_name}, skipping to next trial")
                return False  # Skip to next trial
            
            # DRAW LINES FIRST (so they appear underneath)
            for line in line_stimuli:
                line.draw()
            
            # Then draw background circles with appropriate colors
            for i, bg_circle in enumerate(background_circles):
                if i < len(responses):
                    if i == responses[-1]:  # Last successfully clicked
                        bg_circle.fillColor = 'lightgreen'  # Already completed
                        bg_circle.lineColor = 'yellowgreen'
                        bg_circle.lineWidth = max(1, int(8 * scale_factor))  # Thicker line for last clicked
                    else:
                        bg_circle.fillColor = 'lightgreen'  # Already completed
                        bg_circle.lineColor = 'black'
                        bg_circle.lineWidth = max(1, int(2 * scale_factor))  # Normal line for completed
                elif i in previous_wrong_circles:
                    bg_circle.fillColor = 'lightcoral'  # Previously clicked wrong this connection
                else:
                    bg_circle.fillColor = 'lightgray'
                bg_circle.draw()
            
            # Then draw all stimuli on top
            for stimulus in stimuli:
                stimulus.draw()
            
            # Draw corner labels LAST (so they appear on top of everything)
            for label in corner_labels:
                label.draw()
            
            # Check mouse position and clicks
            mouse_pos = mouse.getPos()
            mouse_clicked = mouse.getPressed()[0]  # Left mouse button
            
            current_hover = None
            for i, bg_circle in enumerate(background_circles):
                if bg_circle.contains(mouse_pos):
                    current_hover = i
                    if i == target_index:  # Correct target
                        bg_circle.fillColor = 'yellow'
                        
                        # Check for click on correct target
                        if mouse_clicked:
                            # Record the connection
                            reaction_time = clock.getTime() * 1000
                            total_time = trial_start_time.getTime() * 1000
                            
                            if len(responses) > 0:
                                connection = f"{sequence[responses[-1]]}-{sequence[i]}"
                                # Draw line UNDERNEATH (will be drawn first in next iteration)
                                line_stimuli.append(visual.Line(win, 
                                                              start=positions[responses[-1]], 
                                                              end=positions[i], 
                                                              color='red', lineWidth=line_width))
                            else:
                                connection = f"Start-{sequence[i]}"
                            
                            # Log only to master file
                            master_log_writer.writerow([filename_prefix, trial_name, connection, 
                                                      reaction_time, total_time, wrong_guesses_this_connection])
                            
                            responses.append(i)
                            found_target = True
                            
                            # Wait for mouse release to prevent double-clicks
                            while mouse.getPressed()[0]:
                                core.wait(0.01)
                            break
                    else:  # Wrong target
                        if i not in previous_wrong_circles:
                            bg_circle.fillColor = 'orange'  # Hovering over wrong target
                        
                        # Check for click on wrong target
                        if mouse_clicked and i not in previous_wrong_circles:
                            bg_circle.fillColor = 'lightcoral'
                            wrong_guesses_this_connection += 1
                            total_errors += 1
                            previous_wrong_circles.add(i)
                            
                            # Wait for mouse release
                            while mouse.getPressed()[0]:
                                core.wait(0.01)
            
            win.flip()
            core.wait(0.01)  # Small delay to prevent excessive CPU usage
    
    # Trial completion feedback with scaled text
    completion_time = trial_start_time.getTime()
    feedback_text = f'Trial Complete!\n\nTotal Time: {completion_time:.2f} seconds\nTotal Errors: {total_errors}\n\nPress any key to continue.'
    feedback = visual.TextStim(win, text=feedback_text, height=feedback_text_size)
    feedback.draw()
    win.flip()
    event.waitKeys()
    
    return True

# Main experiment function
# Main experiment function
def run_experiment():
    # Get participant information
    expInfo = {'Participant ID': '', 'Treatment': ''}
    dlg = gui.DlgFromDict (expInfo)
    if dlg.OK == False:
        core.quit()

    participant_id = expInfo['Participant ID']
    treatment = expInfo['Treatment']

    # Create "Trailmaking Data" subfolder if it doesn't exist
    data_folder = "Trailmaking Data"
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)

    # Create master CSV file with treatment inside the subfolder
    if treatment:
        master_filename = os.path.join(data_folder, f'{participant_id}_{treatment}_TMT_Master.csv')
        filename_prefix = f'{participant_id}_{treatment}'
    else:
        master_filename = os.path.join(data_folder, f'{participant_id}_TMT_Master.csv')
        filename_prefix = participant_id
    
    # Set up PsychoPy window with proper close handling
    win = visual.Window(fullscr=True, monitor='testMonitor', color='black',units='pix', allowGUI=True)
    
    # Get scaling factors for welcome and final messages
    scale_factor = get_scaling_factors(win.size)
    welcome_text_size = int(50 * scale_factor)
    welcome_wrap_width = int(800 * scale_factor)
    
    try:
        with open(master_filename, mode='w', newline='') as master_csvfile:
            master_log_writer = csv.writer(master_csvfile)
            master_log_writer.writerow(['Participant_Treatment', 'Trial_Name', 'Connection', 
                          'Reaction_Time_ms', 'Total_Time_ms', 'Wrong_Guesses_Before_Correct_One'])
            
            # Welcome message with scaled text
            welcome = visual.TextStim(win, 
                                    text='Welcome to the Trail Making Test\n\nYou will complete several trials with different types of stimuli.\n\nClick on each item in the correct sequence.\n\nPress any key to begin.', 
                                    height=welcome_text_size, wrapWidth=welcome_wrap_width)
            welcome.draw()
            win.flip()
            event.waitKeys()
            
            # Define all trials
            trials = []
            
            # Familiarization Trials
            # Familiarization Trials
            trials.extend([
                # Numbers
                ('Familiarization_Numbers_Asc', ['numbers'], 'ascending', 
                 'Familiarization Trial: Numbers Ascending\n\nClick the numbers from 1 to 6 in ascending order.\n\nClick each number in sequence: 1 → 2 → 3 → 4 → 5 → 6\n\nPress any key to start.'),
                ('Familiarization_Numbers_Desc', ['numbers'], 'descending',
                 'Familiarization Trial: Numbers Descending\n\nClick the numbers from 6 to 1 in descending order.\n\nClick each number in sequence: 6 → 5 → 4 → 3 → 2 → 1\n\nPress any key to start.'),
                
                # Letters
                ('Familiarization_Letters_Asc', ['letters'], 'ascending',
                 'Familiarization Trial: Letters Ascending\n\nClick the letters from A to F in ascending order.\n\nClick each letter in sequence: A → B → C → D → E → F\n\nPress any key to start.'),
                ('Familiarization_Letters_Desc', ['letters'], 'descending',
                 'Familiarization Trial: Letters Descending\n\nClick the letters from F to A in descending order.\n\nClick each letter in sequence: F → E → D → C → B → A\n\nPress any key to start.'),
                
                # Shapes
                ('Familiarization_Shapes_Asc', ['shapes'], 'ascending',
                 'Familiarization Trial: Shapes Ascending\n\nClick the shapes from triangle to octagon\n(by increasing number of sides).\n\nSequence: triangle → square → pentagon → hexagon → heptagon → octagon\n\nFor your convenience, shapes are also colored in rainbow color order (Red → Orange → Yellow → Green → Blue → Indigo)\n\nPress any key to start.'),
                ('Familiarization_Shapes_Desc', ['shapes'], 'descending',
                 'Familiarization Trial: Shapes Descending\n\nClick the shapes from octagon to triangle\n(by decreasing number of sides).\n\nSequence: octagon → heptagon → hexagon → pentagon → square → triangle\n\nPress any key to start.'),
                
                # Mixed ascending
                ('Familiarization_Mixed_Asc', ['numbers', 'shapes', 'letters'], 'ascending',
                 'Familiarization Trial: Mixed Ascending\n\nAlternate between numbers, shapes, and letters in ascending order.\n\nSequence: 1 → triangle → A → 2 → square → B → 3 → pentagon → C → 4 → hexagon → D → 5 → heptagon → E → 6 → octagon → F\n\nPress any key to start.'),
                
                # Mixed descending  
                ('Familiarization_Mixed_Desc', ['numbers', 'shapes', 'letters'], 'descending',
                 'Familiarization Trial: Mixed Descending\n\nAlternate between numbers, shapes, and letters in descending order.\n\nSequence: 6 → octagon → F → 5 → heptagon → E → 4 → hexagon → D → 3 → pentagon → C → 2 → square → B → 1 → triangle → A\n\nPress any key to start.')
            ])
            # Experimental Trials
# Experimental Trials - 3 ascending, 3 descending, alternating
            ascending_conditions = [
                ('ascending', ['numbers', 'shapes', 'letters']),
                ('ascending', ['shapes', 'letters', 'numbers']),
                ('ascending', ['letters', 'numbers', 'shapes'])
            ]
            
            descending_conditions = [
                ('descending', ['numbers', 'shapes', 'letters']),
                ('descending', ['shapes', 'letters', 'numbers']),
                ('descending', ['letters', 'numbers', 'shapes'])
            ]
            
            # Randomize within each direction type
            random.shuffle(ascending_conditions)
            random.shuffle(descending_conditions)
            
            # Randomly decide whether to start with ascending or descending
            start_with_ascending = random.choice([True, False])
            
            # Alternate between ascending and descending
            for i in range(3):
                if start_with_ascending:
                    # Add ascending trial
                    direction, category_order = ascending_conditions[i]
                    trial_name = f'Experimental_Ascending_{i+1}'
                    category_str = ' → '.join(category_order)
                    instructions = f'Experimental Trial - Ascending {i+1}\n\nCategory order: {category_str}\n\nPress any key to start.'
                    trials.append((trial_name, category_order, direction, instructions))
                    
                    # Add descending trial
                    direction, category_order = descending_conditions[i]
                    trial_name = f'Experimental_Descending_{i+1}'
                    category_str = ' → '.join(category_order)
                    instructions = f'Experimental Trial - Descending {i+1}\n\nCategory order: {category_str}\n\nPress any key to start.'
                    trials.append((trial_name, category_order, direction, instructions))
                else:
                    # Add descending trial
                    direction, category_order = descending_conditions[i]
                    trial_name = f'Experimental_Descending_{i+1}'
                    category_str = ' → '.join(category_order)
                    instructions = f'Experimental Trial - Descending {i+1}\n\nCategory order: {category_str}\n\nPress any key to start.'
                    trials.append((trial_name, category_order, direction, instructions))
                    
                    # Add ascending trial
                    direction, category_order = ascending_conditions[i]
                    trial_name = f'Experimental_Ascending_{i+1}'
                    category_str = ' → '.join(category_order)
                    instructions = f'Experimental Trial - Ascending {i+1}\n\nCategory order: {category_str}\n\nPress any key to start.'
                    trials.append((trial_name, category_order, direction, instructions))
            
            # Run all trials
            for trial_info in trials:
                trial_name, categories, sequence_type, instructions_text = trial_info
                
                # Create sequence for this trial
                sequence = create_trial_sequence(categories, sequence_type, categories if len(categories) > 1 else None)
                
                print(f"Running {trial_name}: {len(sequence)} items")
                
                # Run trial with labels for experimental trials AND mixed familiarization trials
                if 'Experimental' in trial_name or 'Mixed' in trial_name:
                    if not run_trial(win, trial_name, sequence, instructions_text, filename_prefix, master_log_writer, sequence_type, categories):
                        continue  # Skip to next trial if escape pressed
                else:
                    if not run_trial(win, trial_name, sequence, instructions_text, filename_prefix, master_log_writer):
                        continue  # Skip to next trial if escape pressed
                
                print(f"Completed {trial_name}")
            
            # Final message with scaled text
            final_msg = visual.TextStim(win, text='Experiment Complete!\n\nThank you for participating.\n\nPress any key to exit.', 
                                      height=welcome_text_size, wrapWidth=welcome_wrap_width)
            final_msg.draw()
            win.flip()
            event.waitKeys()

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Cleanup - always close the window
        try:
            win.close()
        except:
            pass
        core.quit()


def draw_instruction_visuals(win, categories, sequence_type, category_order=None, scale_factor=1.0, y_offset=0, do_flip=True):
    """Draws a horizontal row of dots for each category in the order, with their labels."""
    y_start = (200 + y_offset) * scale_factor  # vertical offset for first row
    row_gap = 80 * scale_factor
    dot_radius = 25 * scale_factor
    text_height = 32 * scale_factor
    shape_size = 22 * scale_factor

    # Prepare items for each category
    items = {}
    if 'numbers' in categories:
        items['numbers'] = list(range(1, 7)) if sequence_type == 'ascending' else list(range(6, 0, -1))
    if 'letters' in categories:
        letters = ['A', 'B', 'C', 'D', 'E', 'F']
        items['letters'] = letters if sequence_type == 'ascending' else letters[::-1]
    if 'shapes' in categories:
        shapes = get_shape_names(6)
        items['shapes'] = shapes if sequence_type == 'ascending' else shapes[::-1]

    # Determine order to display rows
    if category_order:
        display_order = category_order
    else:
        display_order = [cat for cat in ['numbers', 'letters', 'shapes'] if cat in categories]

    # Do NOT clearBuffer or flip here!
    for idx, cat in enumerate(display_order):
        y = y_start - idx * row_gap
        x_start = -180 * scale_factor
        for i, val in enumerate(items[cat]):
            x = x_start + i * 65 * scale_factor
            if cat == 'shapes':
                stim = create_shape(win, val, (x, y), size=shape_size, fillColor='white', lineColor='black', scale_factor=1.0)
                stim.draw()
            else:
                stim = visual.Circle(win, radius=dot_radius, pos=(x, y), fillColor='white', lineColor='black')
                stim.draw()
                label = visual.TextStim(win, text=str(val), pos=(x, y), height=text_height, color='black')
                label.draw()
        # Draw category label at left
        cat_label = visual.TextStim(win, text=cat.capitalize(), pos=(x_start - 120 * scale_factor, y), height=text_height, color='red', bold=True)
        cat_label.draw()
    if do_flip:
        win.flip()
# Run the experiment
if __name__ == '__main__':
    run_experiment()
