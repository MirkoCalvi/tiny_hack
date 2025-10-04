extern const int MY_VAR;

/*  TrackDrinkingMovingSM.h  */
#pragma once

#include <Arduino.h> // optional – only for String debugging

class TrackDrinkingMovingSM {
public:
  /* --- State enumeration ----------------------------------- */
  enum class State : uint8_t {
    TRACK,    // initial state: the bottle is laying on the desk and scanning
              // for expressions
    DRINKING, // drinking state: user is drinking; counting time
    MOVING    // bottle is moving, but user is not drinking
  };

  /* --- ctor ------------------------------------------------ */
  TrackDrinkingMovingSM();

  /* --- Transition helpers --------------------------------- */
  bool startDrinking(); // TRACK → DRINKING
  bool stopDrinking();  // DRINKING → TRACK
  bool startMoving();   // TRACK → MOVING
  bool stopMoving();    // MOVING → TRACK

  /* --- Query ------------------------------------------------ */
  State getState() const;

  /* --- Debug helper --------------------------------------- */
  String stateToString() const;

private:
  State currentState;
};
