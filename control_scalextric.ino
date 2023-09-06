// Motor A connections
int enA = 9;
int in1 = 8;
int in2 = 7;

String myCmd;
int num;


void setup() {
  // Set all the motor control pins to outputs
  pinMode(enA, OUTPUT);
  pinMode(in1, OUTPUT);
  pinMode(in2, OUTPUT);
  
  // Turn off motors - Initial state
  analogWrite(enA, 0);
  digitalWrite(in1, LOW);
  digitalWrite(in2, LOW);


  Serial.begin(115200);
}

void loop() {
  

  while(Serial.available()==0){
    
  }
  

  char receivedChar = Serial.read();
  
  if (receivedChar == 'v') {
    
    myCmd=Serial.readStringUntil('\n');
    num=myCmd.toInt();

        if(0 <= num && num < 256){
      cambiarVelocidad(num);
    }else{
      analogWrite(enA, 0);
    }
    Serial.flush();
    
  }
  
  
  
}



void cambiarVelocidad(int velocidad){
  analogWrite(enA, velocidad);
  digitalWrite(in2, HIGH);
}
