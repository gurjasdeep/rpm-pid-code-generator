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
        self.motor_fields = []
        self.create_ui()

    def create_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="MOTOR RPM TUNER", font=("Arial", 20, "bold")).pack(anchor="w", pady=10)
        config = ttk.LabelFrame(main, text="Hardware Configuration", padding=10)
        config.pack(fill="x", pady=5)
        self.add_combo(config, "Microcontroller", self.mcu, ["ESP32", "Arduino", "Teensy", "Pico"], 0)
        self.add_combo(config, "Motor Driver", self.driver, ["BTN8982", "L298N", "MDD20A", "Generic PWM/DIR"], 1)
        self.add_entry(config, "Number of Motors", self.count, 2)
        self.add_entry(config, "PWM Resolution (bits)", self.resolution, 3)
        self.add_entry(config, "PWM Hard Limit (%)", self.pwm_limit, 4)
        self.add_entry(config, "PID Interval (ms)", self.pid_interval, 5)
        ttk.Button(config, text="Update Motor Configuration", command=self.build_motor_fields).grid(row=6, column=0, columnspan=4, pady=10)
        self.hardware_frame = ttk.LabelFrame(main, text="Individual Motor Configuration", padding=10)
        self.hardware_frame.pack(fill="x", pady=8)
        self.build_motor_fields()
        controls = ttk.Frame(main)
        controls.pack(fill="x", pady=8)
        for label, command in [("Generate C++ Code", self.generate), ("Copy Code", self.copy_code), ("Save .ino", self.save_ino), ("Clear", lambda: self.output.delete("1.0", "end"))]:
            ttk.Button(controls, text=label, command=command).pack(side="left", padx=5)
        self.output = tk.Text(main, font=("Consolas", 10), wrap="none", undo=True)
        self.output.pack(fill="both", expand=True)

    @staticmethod
    def add_combo(parent, label, variable, values, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=25).grid(row=row, column=1, sticky="w", padx=5, pady=3)

    @staticmethod
    def add_entry(parent, label, variable, row):
        ttk.Label(parent, text=label).grid(row=row, column=2, sticky="w", padx=5, pady=3)
        ttk.Entry(parent, textvariable=variable, width=12).grid(row=row, column=3, sticky="w", padx=5, pady=3)

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
        for column, name in enumerate(["Motor", *names, "Encoder A", "Encoder B", "Ticks/Rev"]):
            ttk.Label(self.hardware_frame, text=name, font=("Arial", 9, "bold")).grid(row=0, column=column, padx=5)
        for index in range(number):
            ttk.Label(self.hardware_frame, text=f"Motor {index + 1}").grid(row=index + 1, column=0, padx=5, pady=3)
            row, defaults = {}, [2 + index * 6 + offset for offset in range(len(names))] + [4 + index * 2, 5 + index * 2, 600]
            for column, (key, default) in enumerate(zip([*names, "ENC_A", "ENC_B", "TICKS"], defaults), 1):
                entry = ttk.Entry(self.hardware_frame, width=8); entry.grid(row=index + 1, column=column, padx=3)
                entry.insert(0, old[index].get(key, str(default)) if index < len(old) else str(default)); row[key] = entry
            self.motor_fields.append(row)

    def generate(self):
        try:
            count, bits, limit, interval = self.count.get(), self.resolution.get(), self.pwm_limit.get(), self.pid_interval.get()
            if not 1 <= count <= 16 or len(self.motor_fields) != count: raise ValueError("Update motor configuration first.")
            if not 1 <= bits <= 16 or not 1 <= limit <= 100 or not 1 <= interval <= 1000: raise ValueError("Check PWM and PID values.")
            if self.mcu.get() == "Arduino" and bits != 8: raise ValueError("Standard Arduino Uno/Nano uses 8-bit analogWrite. Select 8 bits.")
            motors = [{key: int(entry.get()) for key, entry in row.items()} for row in self.motor_fields]
            pin_values = [value for motor in motors for key, value in motor.items() if key != "TICKS"]
            if any(value < 0 for value in pin_values) or len(pin_values) != len(set(pin_values)): raise ValueError("Pins must be non-negative and unique.")
            if any(motor["TICKS"] == 0 for motor in motors): raise ValueError("Ticks per revolution must be positive.")
            self.output.delete("1.0", "end"); self.output.insert("1.0", self.generate_cpp(motors, bits, limit, interval))
        except (ValueError, tk.TclError) as error: messagebox.showerror("Configuration Error", str(error))

    def generate_cpp(self, motors, bits, limit, interval):
        driver, mcu, number = self.driver.get(), self.mcu.get(), len(motors)
        max_pwm, hard_limit = (1 << bits) - 1, int(((1 << bits) - 1) * limit / 100)
        constants, encoder_constants, objects, setup_pins, cases = [], [], [], [], []
        for index, motor in enumerate(motors):
            if driver == "L298N":
                constants.append(f"const int PWM_{index}={motor['PWM/EN']}, IN1_{index}={motor['IN1']}, IN2_{index}={motor['IN2']};")
                setup_pins.append(f"pinMode(PWM_{index},OUTPUT); pinMode(IN1_{index},OUTPUT); pinMode(IN2_{index},OUTPUT);")
                cases.append(f"case {index}: digitalWrite(IN1_{index},value>=0); digitalWrite(IN2_{index},value<0); writePWM(PWM_{index},abs(value)); break;")
            elif driver == "BTN8982":
                constants.append(f"const int PWM_A_{index}={motor['PWM_A']}, PWM_B_{index}={motor['PWM_B']};")
                setup_pins.append(f"pinMode(PWM_A_{index},OUTPUT); pinMode(PWM_B_{index},OUTPUT);")
                cases.append(f"case {index}: writePWM(PWM_A_{index},value>0?value:0); writePWM(PWM_B_{index},value<0?-value:0); break;")
            else:
                constants.append(f"const int PWM_{index}={motor['PWM']}, DIR_{index}={motor['DIR']};")
                setup_pins.append(f"pinMode(PWM_{index},OUTPUT); pinMode(DIR_{index},OUTPUT);")
                cases.append(f"case {index}: digitalWrite(DIR_{index},value<0); writePWM(PWM_{index},abs(value)); break;")
            encoder_constants.append(f"const int ENC_A_{index}={motor['ENC_A']}, ENC_B_{index}={motor['ENC_B']};")
            objects.append(f"Encoder encoder{index}(ENC_A_{index},ENC_B_{index});")
        ticks = ", ".join(str(motor["TICKS"]) for motor in motors)
        enc_setup = "\n".join(f"    encoders[{index}].attachFullQuad(ENC_A_{index}, ENC_B_{index});" for index in range(number))
        non_esp_counts = "\n".join(
            f"    if (motor == {index}) return encoder{index}.read();"
            for index in range(number)
        ) + "\n    return 0;"
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
float targetRPM[NUM_MOTORS]={{0}}, currentRPM[NUM_MOTORS]={{0}}, kp[NUM_MOTORS]={{0.2}}, ki[NUM_MOTORS]={{0.1}}, kd[NUM_MOTORS]={{0.001}}, integral[NUM_MOTORS]={{0}}, previousError[NUM_MOTORS]={{0}};
long previousCount[NUM_MOTORS]={{0}}; unsigned long previousPID=0, previousSample=0;
bool encoderStreaming=false; int streamMotor=-1; enum Mode {{ PID_MODE, MANUAL_MODE }}; Mode mode=PID_MODE;

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
void updatePID() {{ unsigned long now=millis(); if(now-previousPID<PID_INTERVAL)return; float dt=(now-previousPID)/1000.0f; previousPID=now; if(mode!=PID_MODE)return; for(int i=0;i<NUM_MOTORS;i++){{float error=targetRPM[i]-currentRPM[i]; integral[i]=constrain(integral[i]+error*dt,-1000,1000); float output=kp[i]*error+ki[i]*integral[i]+kd[i]*(error-previousError[i])/dt; previousError[i]=error; setMotor(i,(int)output);}} }}
void processCommand(String command) {{
  command.trim(); command.toLowerCase(); char buffer[120]; command.toCharArray(buffer,sizeof(buffer)); char name[16], argument[16]; int motor; float first,second,third;
  if(sscanf(buffer,"reset %15s",argument)==1) {{ if(!strcmp(argument,"all")){{for(int i=0;i<NUM_MOTORS;i++)resetEncoder(i); Serial.println("All encoders reset");}} else {{motor=atoi(argument); if(motor>=1&&motor<=NUM_MOTORS){{resetEncoder(motor-1);Serial.println("Encoder reset");}} else Serial.println("Invalid motor number");}} return; }}
  if(sscanf(buffer,"encoder %d",&motor)==1 && motor>=1 && motor<=NUM_MOTORS){{streamMotor=motor-1;encoderStreaming=true;Serial.println("Encoder streaming started");return;}}
  if(!strcmp(buffer,"stop")){{encoderStreaming=false;streamMotor=-1;Serial.println("Encoder streaming stopped");return;}}
  if(sscanf(buffer,"target %d %f",&motor,&first)==2 && motor>=1 && motor<=NUM_MOTORS){{targetRPM[motor-1]=first;return;}}
  if(sscanf(buffer,"motor %d %f %f %f",&motor,&first,&second,&third)==4 && motor>=1 && motor<=NUM_MOTORS){{int i=motor-1;kp[i]=first;ki[i]=second;kd[i]=third;integral[i]=previousError[i]=0;return;}}
  if(!strcmp(buffer,"mode pid")){{mode=PID_MODE;return;}} if(!strcmp(buffer,"mode manual")){{mode=MANUAL_MODE;return;}}
  if(!strcmp(buffer,"help")){{Serial.println("motor <n> <kp> <ki> <kd> | target <n> <rpm> | encoder <n> | reset <n|all> | stop | mode pid|manual");return;}} Serial.println("Unknown command. Send help.");
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
void loop() {{ while(Serial.available())processCommand(Serial.readStringUntil('\\n')); sampleRPM(); updatePID(); if(encoderStreaming&&streamMotor>=0){{Serial.print("Encoder: ");Serial.println(encoderCount(streamMotor));delay(50);}} }}
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
