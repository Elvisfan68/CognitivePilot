from psychopy import visual, event, core, gui, data
import numpy as np
import random
import csv
import os
from datetime import datetime

def get_scaling_factors(win_size):
    baseline_width = 1920
    baseline_height = 1080
    
    width_scale = win_size[0] / baseline_width
    height_scale = win_size[1] / baseline_height
    
    scale_factor = min(width_scale, height_scale)
    return scale_factor

def run_pvt_study():
    # Create data folder if it doesn't exist
    data_folder = "PVT Data"
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
    expInfo = {'Participant ID': '', 'Treatment': ''}
    dlg = gui.DlgFromDict(expInfo, title='PVT Study')
    if not dlg.OK:
        core.quit()
    
    participant_id = expInfo['Participant ID']
    treatment = expInfo['Treatment']
    
    win = visual.Window(fullscr=True, monitor='testMonitor', units='pix', 
                       allowGUI=False, color='black')
    
    scale_factor = get_scaling_factors(win.size)
    
    # Scale all elements based on screen size
    counter_size = int(120 * scale_factor)
    instruction_size = int(32 * scale_factor)
    results_size = int(28 * scale_factor)
    
    # Large red counter display - centered on screen
    led_counter = visual.TextStim(win, text='', pos=(0, 0), 
                                 height=counter_size, color='red', 
                                 bold=True)
    
    instruction_text = visual.TextStim(win, text='', pos=(0, -int(300 * scale_factor)), 
                                     height=instruction_size, color='white', 
                                     wrapWidth=int(1200 * scale_factor))
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(data_folder, f'{participant_id}_{treatment}_PVT_{timestamp}.csv')
    
    trials_data = []
    
    try:
        # Instructions
        instructions = '''Psychomotor Vigilance Test

Watch the center of the screen carefully.

When a red number appears, press the SPACEBAR 
as quickly as possible.

The red number shows elapsed time in milliseconds.
React as fast as you can when it appears.

The test will last exactly 5 minutes.

Press ESCAPE to exit at any time
Press SPACEBAR when ready to begin'''
        
        instruction_text.setText(instructions)
        instruction_text.draw()
        win.flip()
        
        # Wait for spacebar or escape
        keys = event.waitKeys(keyList=['space', 'escape'])
        if 'escape' in keys:
            print("Experiment terminated by user during instructions")
            return
        
        # Countdown
        for countdown in [3, 2, 1]:
            countdown_display = visual.TextStim(win, text=f'{countdown}', 
                                              pos=(0, 0), height=int(200 * scale_factor), 
                                              color='white', bold=True)
            countdown_display.draw()
            win.flip()
            
            # Check for escape during countdown
            core.wait(0.5)
            keys = event.getKeys(keyList=['escape'])
            if keys:
                print("Experiment terminated by user during countdown")
                return
            core.wait(0.5)
        
        # "GO" signal
        go_display = visual.TextStim(win, text='BEGIN', pos=(0, 0), 
                                    height=int(150 * scale_factor), 
                                    color='green', bold=True)
        go_display.draw()
        win.flip()
        core.wait(1)
        
        # Main 5-minute test
        test_duration = 300  # 5 minutes
        start_time = core.getTime()
        trial_number = 0
        test_aborted = False
        
        # Show blank screen initially
        win.flip()
        
        while (core.getTime() - start_time) < test_duration and not test_aborted:
            trial_number += 1
            
            # Inter-stimulus interval: 2-10 seconds
            isi = random.uniform(2.0, 10.0)
            isi_start = core.getTime()
            
            # Wait during ISI, checking for responses and escape
            premature_response = False
            while (core.getTime() - isi_start) < isi and not test_aborted:
                win.flip()  # Blank screen
                
                keys = event.getKeys(keyList=['space', 'escape'])
                if 'escape' in keys:
                    print("Experiment terminated by user during ISI")
                    test_aborted = True
                    break
                elif 'space' in keys:
                    premature_response = True
                    # Record false start
                    trials_data.append({
                        'Trial': trial_number,
                        'ISI_ms': isi * 1000,
                        'RT_ms': 'FALSE_START',
                        'Lapse': False,
                        'FalseStart': True,
                        'TimeInTest_s': core.getTime() - start_time
                    })
                    
                    # Show false start feedback
                    false_start_text = visual.TextStim(win, text='FALSE START\nWait for the number!', 
                                                      pos=(0, 0), height=int(60 * scale_factor), 
                                                      color='orange', bold=True)
                    false_start_text.draw()
                    win.flip()
                    core.wait(1.5)
                    break
                
                core.wait(0.01)
            
            if premature_response or test_aborted:
                continue
            
            # Stimulus presentation - large red counter
            stimulus_onset = core.getTime()
            counter_start_time = core.getTime()
            responded = False
            response_time = None
            
            # Display counter until response or timeout
            while not responded and not test_aborted:
                # Calculate elapsed time in milliseconds
                elapsed_ms = (core.getTime() - counter_start_time) * 1000
                
                # Display large counter
                led_counter.setText(f'{int(elapsed_ms)}')
                led_counter.draw()
                win.flip()
                
                # Check for response or escape
                keys = event.getKeys(keyList=['space', 'escape'], timeStamped=True)
                for key, timestamp in keys:
                    if key == 'escape':
                        print("Experiment terminated by user during stimulus")
                        test_aborted = True
                        break
                    elif key == 'space':
                        response_time = (timestamp - stimulus_onset) * 1000
                        responded = True
                        break
                
                # Timeout after 3 seconds (no response = lapse)
                if elapsed_ms > 3000:
                    responded = True
                    response_time = None
            
            if test_aborted:
                break
            
            # Determine if this was a lapse
            is_lapse = (response_time is None) or (response_time > 500)
            
            # Record trial data
            trials_data.append({
                'Trial': trial_number,
                'ISI_ms': isi * 1000,
                'RT_ms': response_time if response_time is not None else 'NO_RESPONSE',
                'Lapse': is_lapse,
                'FalseStart': False,
                'TimeInTest_s': core.getTime() - start_time
            })
            
            # Brief blank screen
            win.flip()
            core.wait(0.1)
            
            # Check if test duration completed
            if (core.getTime() - start_time) >= test_duration:
                break
        
        # Save data to CSV (even if test was aborted)
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['Trial', 'ISI_ms', 'RT_ms', 'Lapse', 'FalseStart', 'TimeInTest_s']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(trials_data)
        
        # Calculate performance variables
        valid_trials = [trial for trial in trials_data 
                       if not trial['FalseStart'] and isinstance(trial['RT_ms'], (int, float))]
        
        if valid_trials:
            # Primary measures
            reaction_times = [trial['RT_ms'] for trial in valid_trials]
            average_response_time = np.mean(reaction_times)
            number_of_lapses = sum(1 for trial in trials_data 
                                 if trial['Lapse'] and not trial['FalseStart'])
            
            # Additional statistics
            median_rt = np.median(reaction_times)
            rt_std = np.std(reaction_times)
            false_starts = sum(1 for trial in trials_data if trial['FalseStart'])
            total_valid_trials = len(valid_trials)
            fastest_10_percent = np.percentile(reaction_times, 10)
            slowest_10_percent = np.percentile(reaction_times, 90)
            
            completion_status = "ABORTED" if test_aborted else "COMPLETED"
            actual_duration = core.getTime() - start_time if 'start_time' in locals() else 0
            
            results_text = f'''5-Minute PVT {completion_status}

Test Duration: {actual_duration:.1f} seconds

PRIMARY MEASURES:
Average Response Time: {average_response_time:.1f} ms
Number of Lapses: {number_of_lapses}

DETAILED STATISTICS:
Total Valid Trials: {total_valid_trials}
Median RT: {median_rt:.1f} ms
RT Variability (SD): {rt_std:.1f} ms
Fastest 10%: {fastest_10_percent:.1f} ms
Slowest 10%: {slowest_10_percent:.1f} ms
False Starts: {false_starts}

Data saved to: {filename}

Press any key to exit'''
        
        else:
            completion_status = "ABORTED" if test_aborted else "COMPLETED"
            results_text = f'''5-Minute PVT {completion_status}

No valid responses recorded.
Please check testing conditions.

Data saved to: {filename}

Press any key to exit'''
        
        # Display results with scaled text
        result_display = visual.TextStim(win, text=results_text, 
                                       height=results_size, color='white',
                                       wrapWidth=int(1200 * scale_factor))
        result_display.draw()
        win.flip()
        event.waitKeys()
        
    except Exception as e:
        print(f"Error during PVT: {e}")
        
    finally:
        win.close()
        core.quit()

if __name__ == '__main__':
    run_pvt_study()