#include <AutoPID.h>

#define REDPIN 11
#define GREENPIN 9
#define BLUEPIN 5
#define WHITEPIN 3

double current_colors[4] = {0, 0, 0, 0};
double target_colors[4] = {0, 0, 0, 0};
double output_colors[4] = {0, 0, 0, 0};

int maxwhite = 255;
int transition_time = 5;

//pid settings and gains
#define OUTPUT_MIN -255
#define OUTPUT_MAX 255

float KP = .75;
float KI = .00;
float KD = .05;

AutoPID PID_red(  &current_colors[0], &target_colors[0], &output_colors[0], OUTPUT_MIN, OUTPUT_MAX, KP, KI, KD);
AutoPID PID_green(&current_colors[1], &target_colors[1], &output_colors[1], OUTPUT_MIN, OUTPUT_MAX, KP, KI, KD);
AutoPID PID_blue( &current_colors[2], &target_colors[2], &output_colors[2], OUTPUT_MIN, OUTPUT_MAX, KP, KI, KD);
AutoPID PID_white(&current_colors[3], &target_colors[3], &output_colors[3], OUTPUT_MIN, OUTPUT_MAX, KP, KI, KD);

String incomingValue1, incomingValue2, incomingValue3, incomingValue4;

void RGB_to_RGBW();

void setup() {
  // put your setup code here, to run once:
  pinMode(REDPIN, OUTPUT);
  pinMode(GREENPIN, OUTPUT);
  pinMode(BLUEPIN, OUTPUT);
  pinMode(WHITEPIN, OUTPUT);
  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);
  Serial.begin(9600);
  Serial.setTimeout(5);
  
  PID_red.setTimeStep(transition_time);
  PID_green.setTimeStep(transition_time);
  PID_blue.setTimeStep(transition_time);
  PID_white.setTimeStep(transition_time);
}

void loop() {
  if (Serial.available() > 0) {
    incomingValue1 = Serial.readStringUntil(',');
    incomingValue2 = Serial.readStringUntil(',');
    incomingValue3 = Serial.readStringUntil(',');
    incomingValue4 = Serial.readStringUntil(',');

    float KP_new = 0.01 * incomingValue4.toFloat();
    if (KP_new != KP){
      KP = KP_new;
      PID_red.setGains(KP, KI, KD);
      PID_green.setGains(KP, KI, KD);
      PID_blue.setGains(KP, KI, KD);
      PID_white.setGains(KP, KI, KD);
    }
    
    target_colors[0] = incomingValue1.toFloat();
    target_colors[1] = incomingValue2.toFloat();
    target_colors[2] = incomingValue3.toFloat();
    RGB_to_RGBW();
  }
  
  PID_red.run();
  PID_green.run();
  PID_blue.run();
  PID_white.run();
  
//  Serial.print("cur: ");
//  Serial.print(current_colors[0]);
//  Serial.print("\ttar: ");
//  Serial.print(target_colors[0]);
//  Serial.print("\tout: ");
//  Serial.println(output_colors[0]);
  
  current_colors[0] = constrain(current_colors[0] + output_colors[0], 0, 255);
  current_colors[1] = constrain(current_colors[1] + output_colors[1], 0, 255);
  current_colors[2] = constrain(current_colors[2] + output_colors[2], 0, 255);
  current_colors[3] = constrain(current_colors[3] + output_colors[3], 0, 255);
  
  analogWrite(REDPIN, current_colors[0]);
  analogWrite(GREENPIN, current_colors[1]);
  analogWrite(BLUEPIN, current_colors[2]);
  analogWrite(WHITEPIN, current_colors[3]);
  
  delay(5);
}

void RGB_to_RGBW() {
  float Ri, Gi, Bi;

  Ri = target_colors[0];
  Gi = target_colors[1];
  Bi = target_colors[2];

  float tM, multiplier, hR, hG, hB, M, m, Luminance;
  double Wo, Ro, Go, Bo;

  tM = max(Ri, max(Gi, Bi));

  //This section serves to figure out what the color with 100% hue is
  if (tM == 0) {
    multiplier = 500000;
  }
  else {
    multiplier = 255.0f / tM;
  }
  hR = Ri * multiplier;
  hG = Gi * multiplier;
  hB = Bi * multiplier;

  //This calculates the Whiteness (not strictly speaking Luminance) of the color
  M = max(hR, max(hG, hB));
  m = min(hR, min(hG, hB));
  Luminance = ((M + m) / 2.0f - 127.5f) * (255.0f / 127.5f) / multiplier;

  //Calculate the output values
  Wo = double(Luminance);
  Bo = double(Bi - Luminance);
  Ro = double(Ri - Luminance);
  Go = double(Gi - Luminance);

  //Trim them so that they are all between 0 and 255
  if (Wo < 0) Wo = 0;
  if (Bo < 0) Bo = 0;
  if (Ro < 0) Ro = 0;
  if (Go < 0) Go = 0;
  if (Wo > 255) Wo = 255;
  if (Bo > 255) Bo = 255;
  if (Ro > 255) Ro = 255;
  if (Go > 255) Go = 255;

  if (Wo > maxwhite) Wo = maxwhite;
  target_colors[0] = Ro;
  target_colors[1] = Go;
  target_colors[2] = Bo;
  target_colors[3] = Wo;

}
