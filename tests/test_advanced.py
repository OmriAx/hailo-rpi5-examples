# tests/test_advanced.py
import pytest
import subprocess
import time
import os
import signal

def run_pipeline(script, input_source, duration=30):
    """Helper function to run a pipeline for a specified duration."""
    process = subprocess.Popen(['python', f'basic_pipelines/{script}', '--input', input_source],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(duration)
    finally:
        # Gracefully terminate the process
        process.send_signal(signal.SIGTERM)
        process.wait()  # Ensure the process has fully exited
    stdout, stderr = process.communicate()
    
    # Debug logging
    print(f"--- Pipeline Output for {script} ---")
    print(stdout.decode())
    print(stderr.decode())
    print("----------------------------------")
    
    return stdout.decode(), stderr.decode()

@pytest.mark.performance
def test_inference_speed():
    """Test inference speed for each model."""
    models = ['detection.py', 'pose_estimation.py', 'instance_segmentation.py']
    for model in models:
        stdout, _ = run_pipeline(model, 'resources/detection0.mp4', duration=60)

        # Try different approaches to capture FPS values
        fps_lines = [line for line in stdout.split('\n') if 'FPS' in line or 'fps' in line]
        
        if not fps_lines:
            print(f"No FPS data found in output for {model}. Raw output:\n{stdout}")
            raise AssertionError(f"FPS data not found for {model}")

        # Handle different formatting cases (in case it's not "FPS: xx" exactly)
        fps_values = []
        for line in fps_lines:
            try:
                # Try extracting float FPS value from the line
                fps_values.append(float(line.split(':')[1].strip().split(',')[0]))
            except (ValueError, IndexError):
                print(f"Failed to parse FPS from line: {line}")

        avg_fps = sum(fps_values) / len(fps_values) if fps_values else 0
        assert avg_fps > 10, f"Average FPS for {model} is below 10 FPS: {avg_fps}"

@pytest.mark.stress
def test_long_running():
    """Test long-running stability."""
    script = 'detection.py'
    process = subprocess.Popen(['python', f'basic_pipelines/{script}', '--input', 'resources/detection0.mp4'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start_time = time.time()
    try:
        while time.time() - start_time < 360:  # Run for 6 minutes
            if process.poll() is not None:
                raise AssertionError(f"Process exited unexpectedly after {time.time() - start_time} seconds")
            time.sleep(10)
    finally:
        # Gracefully terminate the process
        process.send_signal(signal.SIGTERM)
        process.wait()  # Ensure the process has fully exited
        stdout, stderr = process.communicate()

    assert "Error" not in stderr.decode(), f"Errors encountered during long-running test: {stderr.decode()}"


def test_pi_camera_running():
    """Test if the Raspberry Pi camera is accessible and running."""
    # Check if /dev/video0 exists, which is typically where the Pi camera is mapped
    if not os.path.exists('/dev/video0'):
        pytest.skip("No camera detected at /dev/video0")
    

    # Try capturing a frame using the Pi camera
    process = subprocess.Popen(['python', 'basic_pipelines/detection.py', '--input', '/dev/video0'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(10)  # Let the process run for 10 seconds
    finally:
        # Gracefully terminate the process
        process.send_signal(signal.SIGTERM)
        process.wait()  # Ensure the process has fully exited
    
    stdout, stderr = process.communicate()
    print("Pi Camera Test - Stdout:", stdout.decode())
    print("Pi Camera Test - Stderr:", stderr.decode())

    assert "error" not in stderr.decode().lower(), f"Unexpected error when accessing Pi camera: {stderr.decode()}"
    assert process.returncode == 0, f"Pi camera process exited with code {process.returncode}"
