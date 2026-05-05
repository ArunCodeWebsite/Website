```
// Before Uploading, Please Connect Arudino & Rove(Pins) To your Computer
// For More Detail Visit: https://miniature-potato-97g99vw5w5rj3676-5500.app.github.dev/docs, And Go Too: "Arudino/Help"

#include <Arduino.h>

String Command = "Move Forward"; // <-- Edit This Too: "Move Forward", "Move Backwards", "Turn Right", Or "Turn Left"
String Dir = "Clockwise"; // <-- Edit This Too: "Clockwise" Or "Counter Clockwise"

void setup() {
  pinMode(4, OUTPUT);
  pinMode(5, OUTPUT);
  pinMode(6, OUTPUT);
  pinMode(7, OUTPUT);

  Serial.begin(115200);
}

void loop() {
  if (Command == "Move Forward") {
    if (Dir == "Clockwise") {
      digitalWrite(4, HIGH);
      digitalWrite(5, LOW);
      digitalWrite(6, HIGH);
      digitalWrite(7, LOW);
    } else if (Dir == "Counter Clockwise") {
      digitalWrite(4, LOW);
      digitalWrite(5, HIGH);
      digitalWrite(6, LOW);
      digitalWrite(7, HIGH);
    }

  } 
  else if (Command == "Move Backwards") {
    if (Dir == "Clockwise") {
      digitalWrite(4, LOW);
      digitalWrite(5, HIGH);
      digitalWrite(6, LOW);
      digitalWrite(7, HIGH);
    } else if (Dir == "Counter Clockwise") {
      digitalWrite(4, HIGH);
      digitalWrite(5, LOW);
      digitalWrite(6, HIGH);
      digitalWrite(7, LOW);
    }

  } 

  else if (Command == "Turn Right") {
    if (Dir == "Clockwise") {
      digitalWrite(4, HIGH);
      digitalWrite(5, LOW);
      digitalWrite(6, LOW);
      digitalWrite(7, LOW);
    } else if (Dir == "Counter Clockwise") {
      digitalWrite(4, LOW);
      digitalWrite(5, HIGH);
      digitalWrite(6, LOW);
      digitalWrite(7, LOW);
    }

  } 

  else if (Command == "Turn Left") {
    if (Dir == "Clockwise") {
      digitalWrite(4, LOW);
      digitalWrite(5, LOW);
      digitalWrite(6, HIGH);
      digitalWrite(7, LOW);
    } else if (Dir == "Counter Clockwise") {
      digitalWrite(4, LOW);
      digitalWrite(5, LOW);
      digitalWrite(6, LOW);
      digitalWrite(7, HIGH);
    }
  }
}

```