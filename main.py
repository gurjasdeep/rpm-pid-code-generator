import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class MotorTunerGenerator:
    def __init__(self, root):
        self.root = root
        root.title("Motor RPM Tuner - Code Generator")
        root.geometry("1050x850")
        self.driver = tk.StringVar(value="MDD20A")
        self.mcu = tk.StringVar(value="ESP32")
        self.count = tk.IntVar(value=3)
        self.resolution = tk.IntVar(value=10)
        self.pwm_limit = tk.DoubleVar(value=90)
        self.pid_interval = tk.IntVar(value=10)
        self.default_kp = tk.DoubleVar(value=0.2)
        self.default_ki = tk.DoubleVar(value=0.1)
        self.default_kd = tk.DoubleVar(value=0.001)
        self.separate_pid = tk.BooleanVar(value=True)
        self.motor_fields = []
        self.pid_header_widgets = []
        self.pid_widgets = []
        self.create_ui()

    def create_ui(self):
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Save Configuration...", command=self.save_configuration)
        file_menu.add_command(label="Load Configuration...", command=self.load_configuration)
        menu.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menu)

        main = ttk.Frame(self.root, padding=12)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(5, weight=1)
        ttk.Label(main, text="MOTOR RPM TUNER", font=("Arial", 20, "bold")).grid(
            row=0, column=0, sticky="w", pady=10
        )
        config = ttk.LabelFrame(main, text="Hardware Configuration", padding=10)
        config.grid(row=1, column=0, sticky="ew", pady=5, columnspan=2)


        ttk.Label(config, text="Microcontroller").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        ttk.Combobox(config, textvariable=self.mcu, values=["ESP32", "Arduino", "Teensy", "Pico"], state="readonly", width=25).grid(row=0, column=1, sticky="w", padx=5, pady=3)
        ttk.Label(config, text="Motor Driver").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        ttk.Combobox(config, textvariable=self.driver, values=["BTN8982", "L298N", "MDD20A", "Generic PWM/DIR"], state="readonly", width=25).grid(row=1, column=1, sticky="w", padx=5, pady=3)


        ttk.Label(config, text="Number of Motors").grid(row=0, column=2, sticky="w", padx=5, pady=3)
        ttk.Entry(config, textvariable=self.count, width=4).grid(row=0, column=3, sticky="w", padx=5, pady=3)
        ttk.Label(config, text="PWM Resolution (bits)").grid(row=1, column=2, sticky="w", padx=5, pady=3)
        ttk.Entry(config, textvariable=self.resolution, width=4).grid(row=1, column=3, sticky="w", padx=5, pady=3)
        ttk.Label(config, text="PWM Hard Limit (%)").grid(row=2, column=2, sticky="w", padx=5, pady=3)
        ttk.Entry(config, textvariable=self.pwm_limit, width=4).grid(row=2, column=3, sticky="w", padx=5, pady=3)


        ttk.Button(config, text="Update Motor Configuration", command=self.build_motor_fields).grid(row=4, column=0, columnspan=3, pady=10)




        pid_setting = ttk.Frame(config, padding=0)
        pid_setting.grid(row = 0, column=4)
        ttk.Label(pid_setting, text="PID Interval (ms)").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(pid_setting, textvariable=self.pid_interval, width=4).grid(row=0, column=1, sticky="w", padx=5, pady=3)
        ttk.Checkbutton(
            config,
            text="Same PID Constants for all",
            variable=self.separate_pid,
            command=self.update_pid_visibility,
        ).grid(row=1, column=4, rowspan=1, sticky="w", padx=12)


        ttk.Button(config, text="Zero out PID values", command=self.zero_pid_values).grid(
            row=4, column=4, sticky="w", padx=12, pady=0
        )


        self.pid_config = ttk.LabelFrame(main, text="PID Configuration", padding=10)
        self.pid_config.grid(row=2, column=1, sticky="new", pady=5, padx=10)
        ttk.Label(self.pid_config, text="Default kP").grid(row=0, column=2, sticky="w", padx=5, pady=3)
        ttk.Entry(self.pid_config, textvariable=self.default_kp, width=12).grid(row=0, column=3, sticky="w", padx=5, pady=3)
        ttk.Label(self.pid_config, text="Default kI").grid(row=1, column=2, sticky="w", padx=5, pady=3)
        ttk.Entry(self.pid_config, textvariable=self.default_ki, width=12).grid(row=1, column=3, sticky="w", padx=5, pady=3)
        ttk.Label(self.pid_config, text="Default kD").grid(row=2, column=2, sticky="w", padx=5, pady=3)
        ttk.Entry(self.pid_config, textvariable=self.default_kd, width=12).grid(row=2, column=3, sticky="w", padx=5, pady=3)


        self.hardware_frame = ttk.LabelFrame(main, text="Individual Motor Configuration", padding=10)
        self.hardware_frame.grid(row=2, column=0, sticky="ew", pady=8)
        self.build_motor_fields()
        controls = ttk.Frame(main)
        controls.grid(row=4, column=0, sticky="ew", pady=8)
        for column, (label, command) in enumerate([
            ("Generate C++ Code", self.generate),
            ("Copy Code", self.copy_code),
            ("Save .ino", self.save_ino),
            ("Clear", lambda: self.output.delete("1.0", "end")),
        ]):
            ttk.Button(controls, text=label, command=command).grid(row=0, column=column, padx=5)
        self.output = tk.Text(main, font=("Consolas", 10), wrap="none", undo=True)
        self.output.grid(row=5, column=0, sticky="nsew")

    def build_motor_fields(self):
        old = [{key: entry.get() for key, entry in row.items()} for row in self.motor_fields]
        for widget in self.hardware_frame.winfo_children(): widget.destroy()
        self.motor_fields = []
        try:
            number = self.count.get()
            if not 1 <= number <= 16: raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror("Invalid input", "Motor count must be between 1 and 16."); return
        names = ["PWM/EN", "IN1", "IN2"] if self.driver.get() == "L298N" else (["PWM_A", "PWM_B"] if self.driver.get() == "BTN8982" else ["PWM", "DIR"])
        field_names = [*names, "ENC_A", "ENC_B", "TICKS", "KP", "KI", "KD"]
        display_names = ["Motor", *names, "Encoder A", "Encoder B", "Ticks/Rev", "kP", "kI", "kD"]
        self.pid_header_widgets = []
        self.pid_widgets = []
        for column, name in enumerate(display_names):
            header = ttk.Label(self.hardware_frame, text=name, font=("Arial", 9, "bold"))
            header.grid(row=0, column=column, padx=5)
            if name in ("kP", "kI", "kD"):
                self.pid_header_widgets.append(header)
        for index in range(number):
            ttk.Label(self.hardware_frame, text=f"Motor {index + 1}").grid(row=index + 1, column=0, padx=5, pady=3)
            row, defaults = {}, [2 + index * 6 + offset for offset in range(len(names))] + [
                4 + index * 2, 5 + index * 2, 600, self.default_kp.get(), self.default_ki.get(), self.default_kd.get()
            ]
            motor_pid_widgets = []
            for column, (key, default) in enumerate(zip(field_names, defaults), 1):
                entry = ttk.Entry(self.hardware_frame, width=8); entry.grid(row=index + 1, column=column, padx=3)
                entry.insert(0, old[index].get(key, str(default)) if index < len(old) else str(default)); row[key] = entry
                if key in ("KP", "KI", "KD"):
                    motor_pid_widgets.append(entry)
            self.motor_fields.append(row)
            self.pid_widgets.append(motor_pid_widgets)
        self.update_pid_visibility()

    def zero_pid_values(self):
        self.default_kp.set(0)
        self.default_ki.set(0)
        self.default_kd.set(0)
        for row in self.motor_fields:
            for key in ("KP", "KI", "KD"):
                entry = row[key]
                entry.delete(0, "end")
                entry.insert(0, "0")
        self.update_pid_visibility()

    def update_pid_visibility(self):
        if self.separate_pid.get():
            self.pid_config.grid(row=2, column=1, sticky="new", pady=5, padx=10)
            motor_pid_visible = False
        else:
            self.pid_config.grid_remove()
            motor_pid_visible = True
        for widget in self.pid_header_widgets:
            (widget.grid if motor_pid_visible else widget.grid_remove)()
        for motor_pid_widgets in self.pid_widgets:
            for widget in motor_pid_widgets:
                (widget.grid if motor_pid_visible else widget.grid_remove)()


    def get_configuration(self):
        return {
            "format": "motor-rpm-tuner-configuration",
            "version": 1,
            "hardware": {
                "microcontroller": self.mcu.get(),
                "motor_driver": self.driver.get(),
                "motor_count": self.count.get(),
                "pwm_resolution_bits": self.resolution.get(),
                "pwm_hard_limit_percent": self.pwm_limit.get(),
                "pid_interval_ms": self.pid_interval.get(),
            },
            "pid": {
                "default_kp": self.default_kp.get(),
                "default_ki": self.default_ki.get(),
                "default_kd": self.default_kd.get(),
                "separate_gains": self.separate_pid.get(),
            },
            "motors": [
                {
                    key: (float(entry.get()) if key in ("KP", "KI", "KD") else int(entry.get()))
                    for key, entry in row.items()
                }
                for row in self.motor_fields
            ],
        }

    def save_configuration(self):
        try:
            configuration = self.get_configuration()
        except (ValueError, tk.TclError) as error:
            messagebox.showerror("Configuration Error", f"Cannot save configuration: {error}")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Motor configuration", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as output:
                json.dump(configuration, output, indent=2)
                output.write("\n")
        except OSError as error:
            messagebox.showerror("Save Error", f"Could not save configuration:\n{error}")

    def load_configuration(self):
        path = filedialog.askopenfilename(
            filetypes=[("Motor configuration", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as configuration_file:
                configuration = json.load(configuration_file)
            self.apply_configuration(configuration)
        except (OSError, json.JSONDecodeError, ValueError, TypeError, KeyError, tk.TclError) as error:
            messagebox.showerror("Load Error", f"Could not load configuration:\n{error}")

    def apply_configuration(self, configuration):
        if (
            not isinstance(configuration, dict)
            or configuration.get("format") != "motor-rpm-tuner-configuration"
            or configuration.get("version") != 1
        ):
            raise ValueError("This is not a supported motor configuration file.")
        hardware = configuration.get("hardware")
        pid = configuration.get("pid", {})
        motors = configuration.get("motors")
        if not isinstance(hardware, dict) or not isinstance(pid, dict) or not isinstance(motors, list):
            raise ValueError("Configuration must contain hardware and motors sections.")
        if hardware.get("motor_count") != len(motors):
            raise ValueError("Motor count does not match the saved motor entries.")
        if not 1 <= hardware["motor_count"] <= 16:
            raise ValueError("Saved motor count must be between 1 and 16.")
        if hardware["motor_driver"] not in ["BTN8982", "L298N", "MDD20A", "Generic PWM/DIR"]:
            raise ValueError("Saved motor driver is not supported.")
        if hardware["microcontroller"] not in ["ESP32", "Arduino", "Teensy", "Pico"]:
            raise ValueError("Saved microcontroller is not supported.")

        self.mcu.set(hardware["microcontroller"])
        self.driver.set(hardware["motor_driver"])
        self.count.set(hardware["motor_count"])
        self.resolution.set(hardware["pwm_resolution_bits"])
        self.pwm_limit.set(hardware["pwm_hard_limit_percent"])
        self.pid_interval.set(hardware["pid_interval_ms"])
        for key, variable in (
            ("default_kp", self.default_kp),
            ("default_ki", self.default_ki),
            ("default_kd", self.default_kd),
        ):
            if key in pid:
                if not isinstance(pid[key], (int, float)) or isinstance(pid[key], bool):
                    raise ValueError(f"PID field {key} must be a number.")
                variable.set(pid[key])
        if "separate_gains" in pid:
            if not isinstance(pid["separate_gains"], bool):
                raise ValueError("PID field separate_gains must be a boolean.")
            self.separate_pid.set(pid["separate_gains"])
        self.build_motor_fields()
        for row in self.motor_fields:
            for key in ("KP", "KI", "KD"):
                row[key].configure(state="normal")
        expected_keys = set(self.motor_fields[0]) if self.motor_fields else set()
        legacy_keys = expected_keys - {"KP", "KI", "KD"}
        for index, motor in enumerate(motors):
            if not isinstance(motor, dict) or set(motor) not in (legacy_keys, expected_keys):
                raise ValueError(f"Motor {index + 1} has invalid pinout fields.")
            for key, entry in self.motor_fields[index].items():
                if key not in motor:
                    value = {"KP": self.default_kp.get(), "KI": self.default_ki.get(), "KD": self.default_kd.get()}[key]
                else:
                    value = motor[key]
                if key in ("KP", "KI", "KD"):
                    if not isinstance(value, (int, float)) or isinstance(value, bool):
                        raise ValueError(f"Motor {index + 1} field {key} must be a number.")
                elif not isinstance(value, int) or isinstance(value, bool):
                    raise ValueError(f"Motor {index + 1} field {key} must be an integer.")
                entry.delete(0, "end")
                entry.insert(0, str(value))
        self.update_pid_visibility()

    def generate(self):
        try:
            count, bits, limit, interval = self.count.get(), self.resolution.get(), self.pwm_limit.get(), self.pid_interval.get()
            kp, ki, kd = self.default_kp.get(), self.default_ki.get(), self.default_kd.get()
            if not 1 <= count <= 16 or len(self.motor_fields) != count: raise ValueError("Update motor configuration first.")
            if not 1 <= bits <= 16 or not 1 <= limit <= 100 or not 1 <= interval <= 1000: raise ValueError("Check PWM and PID values.")
            if kp < 0 or ki < 0 or kd < 0: raise ValueError("PID values must be non-negative.")
            if self.mcu.get() == "Arduino" and bits != 8: raise ValueError("Standard Arduino Uno/Nano uses 8-bit analogWrite. Select 8 bits.")
            motors = [{
                key: (float(entry.get()) if key in ("KP", "KI", "KD") else int(entry.get()))
                for key, entry in row.items()
            } for row in self.motor_fields]
            pid_values = (
                [(kp, ki, kd)] * count
                if self.separate_pid.get()
                else [(motor["KP"], motor["KI"], motor["KD"]) for motor in motors]
            )
            if any(value < 0 for values in pid_values for value in values):
                raise ValueError("PID values must be non-negative.")
            pin_values = [
                value for motor in motors
                for key, value in motor.items()
                if key not in ("TICKS", "KP", "KI", "KD")
            ]
            if any(value < -1 for value in pin_values):
                raise ValueError("Pins must be -1 or non-negative.")
            if any(motor["ENC_A"] < 0 or motor["ENC_B"] < 0 for motor in motors):
                raise ValueError("Encoder pins must be non-negative.")
            used_pins = [value for value in pin_values if value != -1]
            if len(used_pins) != len(set(used_pins)):
                raise ValueError("Pins must be unique.")
            if any(motor["TICKS"] == 0 for motor in motors): raise ValueError("Ticks per revolution must be positive.")
            self.output.delete("1.0", "end")
            self.output.insert("1.0", self.generate_cpp(motors, bits, limit, interval, kp, ki, kd, pid_values))
        except (ValueError, tk.TclError) as error: messagebox.showerror("Configuration Error", str(error))

    def generate_cpp(self, motors, bits, limit, interval, kp, ki, kd, pid_values=None):
        driver, mcu, number = self.driver.get(), self.mcu.get(), len(motors)
        max_pwm, hard_limit = (1 << bits) - 1, int(((1 << bits) - 1) * limit / 100)
        constants, encoder_constants, objects, setup_pins, cases = [], [], [], [], []
        for index, motor in enumerate(motors):
            if driver == "L298N":
                constants.append(f"const int PWM_{index}={motor['PWM/EN']}, IN1_{index}={motor['IN1']}, IN2_{index}={motor['IN2']};")
                setup_pins.append(
                    f"if(PWM_{index}>=0)pinMode(PWM_{index},OUTPUT); "
                    f"if(IN1_{index}>=0)pinMode(IN1_{index},OUTPUT); "
                    f"if(IN2_{index}>=0)pinMode(IN2_{index},OUTPUT);"
                )
                cases.append(
                    f"case {index}: if(IN1_{index}>=0)digitalWrite(IN1_{index},value>=0); "
                    f"if(IN2_{index}>=0)digitalWrite(IN2_{index},value<0); "
                    f"if(PWM_{index}>=0)writePWM(PWM_{index},abs(value)); break;"
                )
            elif driver == "BTN8982":
                constants.append(f"const int PWM_A_{index}={motor['PWM_A']}, PWM_B_{index}={motor['PWM_B']};")
                setup_pins.append(
                    f"if(PWM_A_{index}>=0)pinMode(PWM_A_{index},OUTPUT); "
                    f"if(PWM_B_{index}>=0)pinMode(PWM_B_{index},OUTPUT);"
                )
                cases.append(
                    f"case {index}: if(PWM_A_{index}>=0)writePWM(PWM_A_{index},value>0?value:0); "
                    f"if(PWM_B_{index}>=0)writePWM(PWM_B_{index},value<0?-value:0); break;"
                )
            else:
                constants.append(f"const int PWM_{index}={motor['PWM']}, DIR_{index}={motor['DIR']};")
                setup_pins.append(
                    f"if(PWM_{index}>=0)pinMode(PWM_{index},OUTPUT); "
                    f"if(DIR_{index}>=0)pinMode(DIR_{index},OUTPUT);"
                )
                cases.append(
                    f"case {index}: if(DIR_{index}>=0)digitalWrite(DIR_{index},value<0); "
                    f"if(PWM_{index}>=0)writePWM(PWM_{index},abs(value)); break;"
                )
            encoder_constants.append(f"const int ENC_A_{index}={motor['ENC_A']}, ENC_B_{index}={motor['ENC_B']};")
            objects.append(f"Encoder encoder{index}(ENC_A_{index},ENC_B_{index});")
        ticks = ", ".join(str(motor["TICKS"]) for motor in motors)
        enc_setup = "\n".join(f"    encoders[{index}].attachFullQuad(ENC_A_{index}, ENC_B_{index});" for index in range(number))
        non_esp_counts = "\n".join(
            f"    if (motor == {index}) return encoder{index}.read();"
            for index in range(number)
        ) + "\n    return 0;"
        pid_values = pid_values or [(kp, ki, kd)] * number
        default_kp = ", ".join(f"{values[0]}f" for values in pid_values)
        default_ki = ", ".join(f"{values[1]}f" for values in pid_values)
        default_kd = ", ".join(f"{values[2]}f" for values in pid_values)
        pid_declarations = (
            f"float kp[NUM_MOTORS] = {{{default_kp}}}, ki[NUM_MOTORS] = {{{default_ki}}}, "
            f"kd[NUM_MOTORS] = {{{default_kd}}};"
        )
        pid_update = "kp[i]*error+ki[i]*integral[i]+kd[i]*(error-previousError[i])/dt"
        pid_command = "kp[i]=first;ki[i]=second;kd[i]=third;"
        return f'''/* Motor RPM Tuner | MCU: {mcu} | Driver: {driver}
   ESP32 uses ESP32Encoder full quadrature. Other boards use Encoder.h.
   PWM uses analogWriteResolution/analogWrite; no PWM frequency is configured. */
#include <Arduino.h>
#if defined(ESP32)
#include <ESP32Encoder.h>
#else
#include <Encoder.h>
#endif
#define NUM_MOTORS {number}
#define PWM_BITS {bits}
#define PWM_LIMIT {hard_limit}
#define PID_INTERVAL {interval}
{chr(10).join(constants)}
{chr(10).join(encoder_constants)}
const int encoderTicks[NUM_MOTORS] = {{{ticks}}};
#if defined(ESP32)
ESP32Encoder encoders[NUM_MOTORS];
#else
{chr(10).join(objects)}
#endif
float targetRPM[NUM_MOTORS]={{0}}, currentRPM[NUM_MOTORS]={{0}}, integral[NUM_MOTORS]={{0}}, previousError[NUM_MOTORS]={{0}};
{pid_declarations}
long previousCount[NUM_MOTORS]={{0}}; unsigned long previousPID=0, previousSample=0;
bool encoderStreaming=false; int streamMotor=-1; enum Mode {{ PID_MODE, MANUAL_MODE }}; Mode mode=PID_MODE;
int manualPWM[NUM_MOTORS]={{0}}; unsigned long manualEnd[NUM_MOTORS]={{0}};

long encoderCount(int motor) {{
#if defined(ESP32)
    return encoders[motor].getCount();
#else
{non_esp_counts}
#endif
}}
void resetEncoder(int motor) {{
#if defined(ESP32)
    encoders[motor].clearCount();
#else
    if (motor == 0) encoder0.write(0);
{chr(10).join(f'    else if (motor == {index}) encoder{index}.write(0);' for index in range(1, number))}
#endif
    previousCount[motor]=0;
}}
void writePWM(int pin, int value) {{ analogWrite(pin, constrain(value, 0, PWM_LIMIT)); }}
void setMotor(int motor, int value) {{ value=constrain(value,-PWM_LIMIT,PWM_LIMIT); switch(motor) {{ {chr(10).join(cases)} }} }}
void sampleRPM() {{ unsigned long now=millis(); if(now-previousSample<100)return; float dt=(now-previousSample)/1000.0f; if(!previousSample){{previousSample=now;return;}} for(int i=0;i<NUM_MOTORS;i++){{long count=encoderCount(i); currentRPM[i]=(count-previousCount[i])*60.0f/(encoderTicks[i]*dt); previousCount[i]=count;}} previousSample=now; }}
void updatePID() {{ unsigned long now=millis(); if(now-previousPID<PID_INTERVAL)return; float dt=(now-previousPID)/1000.0f; previousPID=now; if(mode!=PID_MODE)return; for(int i=0;i<NUM_MOTORS;i++){{float error=targetRPM[i]-currentRPM[i]; integral[i]=constrain(integral[i]+error*dt,-1000,1000); float output={pid_update}; previousError[i]=error; setMotor(i,(int)output);}} }}
void updateManual() {{ for(int i=0;i<NUM_MOTORS;i++){{ if(manualEnd[i] && (long)(millis()-manualEnd[i])>=0){{ setMotor(i,0); manualPWM[i]=0; manualEnd[i]=0; }} }} }}
void processCommand(String command) {{
  command.trim(); command.toLowerCase(); char buffer[120]; command.toCharArray(buffer,sizeof(buffer)); char name[16], argument[16]; int motor; unsigned long duration; float first,second,third;
  if(sscanf(buffer,"reset %15s",argument)==1) {{ if(!strcmp(argument,"all")){{for(int i=0;i<NUM_MOTORS;i++)resetEncoder(i); Serial.println("All encoders reset");}} else {{motor=atoi(argument); if(motor>=1&&motor<=NUM_MOTORS){{resetEncoder(motor-1);Serial.println("Encoder reset");}} else Serial.println("Invalid motor number");}} return; }}
  if(sscanf(buffer,"encoder %d",&motor)==1 && motor>=1 && motor<=NUM_MOTORS){{streamMotor=motor-1;encoderStreaming=true;Serial.println("Encoder streaming started");return;}}
  if(!strcmp(buffer,"stop")){{encoderStreaming=false;streamMotor=-1;Serial.println("Encoder streaming stopped");return;}}
  if(sscanf(buffer,"target %d %f",&motor,&first)==2 && motor>=1 && motor<=NUM_MOTORS){{targetRPM[motor-1]=first;return;}}
  if(sscanf(buffer,"motor %d %f %f %f",&motor,&first,&second,&third)==4 && motor>=1 && motor<=NUM_MOTORS){{int i=motor-1;{pid_command}integral[i]=previousError[i]=0;return;}}
  if(sscanf(buffer,"set %d %f %lu",&motor,&first,&duration)==3 && motor>=1 && motor<=NUM_MOTORS){{ if(mode!=MANUAL_MODE){{Serial.println("Switch to manual mode first");return;}} int i=motor-1; manualPWM[i]=constrain((int)first,-PWM_LIMIT,PWM_LIMIT); manualEnd[i]=millis()+duration; setMotor(i,manualPWM[i]); Serial.println("Manual movement started"); return; }}
  if(!strcmp(buffer,"mode pid")){{mode=PID_MODE;return;}} if(!strcmp(buffer,"mode manual")){{mode=MANUAL_MODE;return;}}
  if(!strcmp(buffer,"help")){{Serial.println("motor <n> <kp> <ki> <kd> | target <n> <rpm> | set <n> <pwm> <time_ms> | encoder <n> | reset <n|all> | stop | mode pid|manual");return;}} Serial.println("Unknown command. Send help.");
}}
void setup() {{ Serial.begin(115200);
#if defined(ESP32) || defined(TEENSYDUINO) || defined(ARDUINO_ARCH_RP2040)
    analogWriteResolution(PWM_BITS);
#endif
    {chr(10).join(setup_pins)}
#if defined(ESP32)
    ESP32Encoder::useInternalWeakPullResistors=UP;\n{enc_setup}
#endif
    for(int i=0;i<NUM_MOTORS;i++)setMotor(i,0); Serial.println("Motor RPM Tuner Ready"); }}
void loop() {{ while(Serial.available())processCommand(Serial.readStringUntil('\\n')); sampleRPM(); updatePID(); updateManual(); if(encoderStreaming&&streamMotor>=0){{Serial.print("Encoder: ");Serial.println(encoderCount(streamMotor));delay(50);}} }}
'''

    def copy_code(self):
        code = self.output.get("1.0", "end-1c")
        if not code.strip(): messagebox.showwarning("No code", "Generate code first."); return
        self.root.clipboard_clear(); self.root.clipboard_append(code); self.root.update()

    def save_ino(self):
        code = self.output.get("1.0", "end-1c")
        if not code.strip(): messagebox.showwarning("No code", "Generate code first."); return
        path = filedialog.asksaveasfilename(defaultextension=".ino", filetypes=[("Arduino sketch", "*.ino")])
        if path:
            with open(path, "w", encoding="utf-8") as output: output.write(code)


if __name__ == "__main__":
    root = tk.Tk(); MotorTunerGenerator(root); root.mainloop()
