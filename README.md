# Motor RPM PID Code Generator

A desktop Tkinter application that generates ready-to-upload Arduino C++ code for tuning and controlling multiple DC motors by RPM. Configure your hardware in the GUI, generate the sketch, then use the serial monitor to tune PID gains, set target speeds, inspect encoder counts, and switch between PID and manual modes.

## Index

- [What It Does](#what-it-does)
- [Why This Exists](#why-this-exists)
- [Use Cases and Test Workflows](#use-cases-and-test-workflows)
	- [Pinout and Motor-Direction Testing](#pinout-and-motor-direction-testing)
	- [Encoder Wiring and Direction Testing](#encoder-wiring-and-direction-testing)
	- [Encoder-Only Testing](#encoder-only-testing)
	- [Encoder Ticks-Per-Revolution Measurement](#encoder-ticks-per-revolution-measurement)
	- [PID Tuning and Speed-Response Testing](#pid-tuning-and-speed-response-testing)
	- [Multi-Motor Isolation and Configuration Testing](#multi-motor-isolation-and-configuration-testing)
- [Supported Motor Drivers](#supported-motor-drivers)
- [Supported Microcontrollers](#supported-microcontrollers)
- [Configurable Values](#configurable-values)
	- [Hardware Configuration](#hardware-configuration)
	- [Per-Motor Configuration](#per-motor-configuration)
	- [Runtime PID Values](#runtime-pid-values)
- [Serial Commands](#serial-commands)
- [Measuring Encoder Ticks per Revolution](#measuring-encoder-ticks-per-revolution)
	- [Method 1: Rotate the Motor by Hand](#method-1-rotate-the-motor-by-hand)
	- [Method 2: Run One Revolution with `set`](#method-2-run-one-revolution-with-set)
- [Tuning the RPM PID Controller](#tuning-the-rpm-pid-controller)
- [Usage](#usage)
- [Requirements](#requirements)
- [Notes](#notes)

## What It Does

- Generates a complete Arduino `.ino` sketch for one or more motors.
- Supports up to 16 independently configured motors.
- Measures motor speed from quadrature encoders and calculates RPM.
- Applies per-motor PID control using configurable `Kp`, `Ki`, and `Kd` values. The generated sketch always supports different gains for different motors.
- Supports encoder reset and live encoder-count streaming over Serial.
- Lets you copy generated code to the clipboard or save it directly as an `.ino` file.
- Lets you save and load complete hardware and motor pinout configurations as human-readable JSON files from the **File** menu.

## Why This Exists

Motor and encoder bring-up required repeating the same tests regularly. Each time, we had to search through old sketches or write a new one for pinout checks, encoder measurements, and PID tuning. That made testing slower and made it easy for different team members or test sessions to use inconsistent code.

This application provides one reusable workflow that generates stable and uniform code for each test case. Hardware settings, motor mappings, encoder checks, manual tests, and PID configurations can be recreated consistently instead of being rebuilt from scratch every time.

## Use Cases and Test Workflows

The generated sketch can be used as a bring-up and diagnostic tool before running a full robot application. Use a serial monitor at **115200 baud** and send each command followed by a newline. Test one motor at a time, keep the motor unloaded when possible, and be ready to remove power if wiring behaves unexpectedly.

### Use-Case Command Formats

These are the command formats used throughout the workflows below. Replace `<n>` with a one-based motor number:

| Command format | Purpose |
| --- | --- |
| `mode manual` | Enable direct timed PWM commands |
| `mode pid` | Enable closed-loop PID control |
| `set <n> <pwm> <time_ms>` | Run motor `<n>` at signed PWM for a limited time |
| `target <n> <rpm>` | Set the target RPM for motor `<n>` |
| `motor <n> <kp> <ki> <kd>` | Set PID gains for motor `<n>` |
| `encoder <n>` | Stream encoder counts for motor `<n>` |
| `reset <n>` | Reset one encoder |
| `reset all` | Reset every encoder |
| `stop` | Stop encoder streaming |

PWM values are signed for direction. The configured PWM hard limit still applies. Commands are newline-terminated, and motor numbers start at `1`.

### Pinout and Motor-Direction Testing

Use manual mode to verify that each motor driver's PWM and direction pins are connected to the expected motor and that positive and negative commands produce the intended directions.

1. Enter the correct driver pins for every motor. Set unused motor-control pins to `-1`.
2. Generate, compile, and upload the sketch.
3. Switch to manual mode:

	```text
	mode manual
	```

4. Test one motor at a low PWM value:

	```text
	set 1 100 2000
	set 1 -100 2000
	```

5. Confirm that motor 1 moves for two seconds in each direction. Repeat for each motor by changing the motor number.
6. If a motor moves in the wrong direction, swap the motor leads, invert the direction wiring or logic as appropriate for the driver, and repeat the test.

For a single-motor test, set the other motors' output pins to `-1`. The generated code skips `pinMode`, `digitalWrite`, and `analogWrite` for disabled `-1` motor pins.

### Encoder Wiring and Direction Testing

Use encoder streaming to verify that both encoder channels are connected and that quadrature direction is reported correctly.

1. Upload a sketch with valid `Encoder A`, `Encoder B`, and `Ticks/Rev` values. Motor output pins may all be `-1`.
2. Reset the selected encoder and begin streaming:

	```text
	reset 1
	encoder 1
	```

3. Rotate the shaft slowly in the expected forward direction and observe the `Encoder: <count>` values.
4. Rotate it in reverse. Counts should change in the opposite direction.
5. If counts do not change, check power, ground, both encoder channels, pull-ups, and the selected pins. If counts change but the direction is reversed, swap encoder A and B or reverse the direction convention in the robot software.
6. Stop streaming when finished:

	```text
	stop
	```

This also helps detect intermittent wiring, missing quadrature transitions, and encoders connected to the wrong motor index.

### Encoder-Only Testing

The generator supports a safe encoder-only sketch. Set every motor-control pin to `-1`, keep encoder pins valid, and set PID values to zero. The sketch will still initialize, reset, stream, and count encoders without attempting to use an invalid motor pin.

Use:

```text
reset all
encoder 1
# Rotate motor 1 or its encoder shaft.
stop
```

This is useful for testing encoders on a workbench, checking encoder direction without motor power, and validating the encoder library and board pin assignments.

### Encoder Ticks-Per-Revolution Measurement

Measure the mechanical ticks per shaft revolution before relying on RPM values. The detailed procedures are in [Measuring Encoder Ticks per Revolution](#measuring-encoder-ticks-per-revolution). The two supported approaches are:

- Rotate the shaft by hand while streaming counts.
- Run one controlled revolution in manual mode using `set`.

Repeat measurements in both directions and average them when possible. Enter the measured result in that motor's `Ticks/Rev` field and regenerate the sketch.

### PID Tuning and Speed-Response Testing

Use the generated per-motor PID arrays to tune motors independently. Start in manual mode to verify wiring, then switch to PID mode only after the encoder and ticks-per-revolution value are confirmed.

1. Choose a conservative target RPM.
2. Start with `Ki` and `Kd` at zero and increase `Kp` gradually.
3. Add a small `Ki` value to correct steady-state error.
4. Add or adjust `Kd` to reduce overshoot and oscillation.
5. Test several target speeds and loads, and record the gains that provide stable response.

Example command sequence:

```text
mode pid
motor 1 0.1 0 0
reset 1
target 1 60
motor 1 0.2 0.05 0.001
target 1 120
```

The GUI's shared PID defaults are convenient for initial multi-motor tests. Uncheck the shared-default option to enter separate gains in each motor row. Runtime `motor <n> ...` commands always update only the selected motor.

### Multi-Motor Isolation and Configuration Testing

The sketch can also verify that motor indices, encoder indices, driver channels, and saved configurations are mapped consistently.

- Run the same low-PWM manual test on each motor and confirm only the requested motor moves.
- Stream each encoder separately and confirm that the count belongs to the corresponding motor.
- Use `reset <n>` and `reset all` to verify individual and global encoder reset behavior.
- Save a known-good configuration, change the GUI values, then load it again to verify configuration restoration.
- Use `mode manual` and timed `set` commands to check that each motor stops automatically after its requested duration.

Example multi-motor sequence:

```text
mode manual
set 1 100 1500
set 2 100 1500
set 3 -100 1500
reset all
encoder 1
stop
encoder 2
stop
```

## Supported Motor Drivers

The generator supports these motor drivers:

| Motor driver | Generated motor-control pins |
| --- | --- |
| `BTN8982` | `PWM_A`, `PWM_B` |
| `L298N` | `PWM/EN`, `IN1`, `IN2` |
| `MDD20A` | `PWM`, `DIR` |
| `Generic PWM/DIR` | `PWM`, `DIR` |

Each motor also has separate `Encoder A`, `Encoder B`, and `Ticks/Rev` fields.

## Supported Microcontrollers

The GUI explicitly supports:

- **ESP32**: uses `ESP32Encoder` and full-quadrature encoder support.
- **Arduino**: intended for standard Arduino boards such as the Uno and Nano; use 8-bit PWM resolution.
- **Teensy**: uses Arduino-compatible PWM and encoder code.
- **Pico**: uses Arduino-compatible PWM and encoder code.

The generated sketch selects the ESP32 encoder library when compiling for ESP32 and `Encoder.h` for other supported boards. Install the required encoder library for your selected platform before compiling.

## Configurable Values

### Hardware configuration

- Microcontroller
- Motor driver
- Number of motors: 1 to 16
- PWM resolution: 1 to 16 bits
- PWM hard limit: 1% to 100%
- PID update interval: 1 to 1000 ms

### PID configuration

- Default `kP`, `kI`, and `kD` values used in the generated sketch
- **Use the same PID defaults for all motors (testing)**: the GUI's default fields provide a convenient common starting point; the generated sketch always stores and applies gains independently for every motor
- **Zero All PID Values**: sets the three default PID values to zero before code generation

### Per-motor configuration

- Driver-specific motor-control pins
- Encoder A pin
- Encoder B pin
- Encoder ticks per revolution
- Per-motor `kP`, `kI`, and `kD` values when shared PID defaults are unchecked

Pins must be unique across the complete configuration. Motor-control pins may be set to `-1` to disable motor output for encoder-only testing; encoder pins must be non-negative. Ticks per revolution must be positive.

### Runtime PID values

The generated sketch starts with the PID gains entered in the PID Configuration section. The default values are:

```text
Kp = 0.2
Ki = 0.1
Kd = 0.001
```

These values can be changed at runtime through the serial monitor without regenerating the sketch.

## Serial Commands

Open the serial monitor at **115200 baud** and send newline-terminated commands:

| Command | Description |
| --- | --- |
| `motor <n> <kp> <ki> <kd>` | Set PID gains for motor `n`. |
| `target <n> <rpm>` | Set the target RPM for motor `n`. |
| `set <n> <pwm> <time_ms>` | In manual mode, run motor `n` at signed PWM for the specified time. |
| `encoder <n>` | Start streaming encoder counts for motor `n`. |
| `reset <n>` | Reset one motor encoder. |
| `reset all` | Reset every encoder. |
| `stop` | Stop encoder streaming. |
| `mode pid` | Enable PID control. |
| `mode manual` | Disable PID control. |
| `help` | Print the command list. |

Motor numbers are one-based, so the first motor is motor `1`.

In manual mode, use a signed PWM value to choose direction. For example, `set 1 400 2000` runs motor 1 at PWM 400 for 2 seconds, then stops it automatically. The configured PWM hard limit is applied to the requested value. Switch to manual mode before using this command:

```text
mode manual
set 1 400 2000
```

## Measuring Encoder Ticks per Revolution

Measure the encoder before generating the final sketch, then enter the measured value in that motor's `Ticks/Rev` field.

### Method 1: Rotate the motor by hand

1. Upload the generated sketch with a temporary encoder configuration.
2. Send `encoder 1` to start streaming counts.
3. Send `reset 1` immediately before each measurement to clear motor 1's encoder count.
4. Mark the motor shaft and rotate it exactly one mechanical revolution by hand.
5. Read the final `Encoder: <count>` value. Because the count was reset before the measurement, this value is directly the ticks for one revolution.
6. Send `stop` to end streaming.

Repeat the reset-and-measure process in both directions and average several readings when possible.

```text
encoder 1
# Rotate motor 1 exactly one revolution by hand.
reset 1
stop
```

### Method 2: Run one revolution with `set`

This method is useful when the motor can rotate freely and you want to measure while powered:

1. Switch to manual mode.
2. Start encoder streaming.
3. Send `reset 1` immediately before the measurement.
4. Run the motor at a low PWM for long enough to make exactly one revolution. Use a visible mark on the shaft or coupler to identify the start and end position.
5. Read the final encoder count directly, then stop streaming. Since the count was reset before the revolution, no subtraction is needed.

```text
mode manual
encoder 1
reset 1
set 1 200 3000
stop
```

The PWM value and duration above are examples only. Adjust them for the motor and load. The `set` command stops the motor automatically after the requested time, and the configured PWM hard limit still applies. Use the final encoder count as `Ticks/Rev`, then repeat the reset-and-measure process to confirm the result.

## Tuning the RPM PID Controller

Tune one motor at a time with the motor unloaded or under its normal operating load. The following example tunes motor 1 to 60 RPM:

1. Start with a conservative controller and clear the encoder:

	```text
	mode pid
	motor 1 0.1 0 0
	reset 1
	target 1 60
	```

2. Increase `Kp` gradually until the motor approaches the target speed. For example:

	```text
	motor 1 0.2 0 0
	motor 1 0.4 0 0
	```

3. Add a small `Ki` value to reduce steady-state speed error:

	```text
	motor 1 0.4 0.05 0
	motor 1 0.4 0.1 0
	```

4. If the motor overshoots or oscillates, reduce `Kp` or `Ki` and add a small `Kd` value to damp the response:

	```text
	motor 1 0.3 0.05 0.001
	```

5. Change the target speed to test the final gains:

	```text
	target 1 120
	```

The `motor` command updates gains immediately and resets that motor's integral and previous-error terms. The sketch calculates RPM from encoder counts internally; use the motor's measured behavior and an external tachometer or telemetry tool to verify the actual RPM while tuning.

## Usage

1. Run the Python application:

	```bash
	python main.py
	```

2. Select the microcontroller and motor driver.
3. Set the global hardware values and click **Update Motor Configuration**.
4. Enter the pins and encoder ticks per revolution for each motor.
5. Click **Generate C++ Code**.
6. Copy the output or save it as an Arduino `.ino` sketch.
7. Install the required encoder library, compile the sketch, and upload it to the microcontroller.
8. Use the serial commands to set target RPMs and tune the PID gains.

Use **File > Save Configuration...** to save the current hardware settings and motor pinouts
as an indented JSON file. Use **File > Load Configuration...** to restore them; loading a
configuration automatically changes the motor count and driver before restoring its saved fields.

## Requirements

- Python 3
- Tkinter, included with most Python installations
- Arduino IDE or another Arduino-compatible build environment
- `ESP32Encoder` when compiling for ESP32
- `Encoder` when compiling for other supported boards

## Notes

- The generated code uses `analogWrite` and configures PWM resolution where the selected platform supports `analogWriteResolution`.
- The sketch samples RPM approximately every 100 ms.
- Choose pins that support the required PWM, digital I/O, and interrupt/encoder functions on your specific board.
