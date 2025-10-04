#include "StateMachine.h"

#pragma once

/* ---------- ctor -------------------------------------------- */
TrackDrinkingMovingSM::TrackDrinkingMovingSM() : currentState(State::TRACK) {}

/* ---------- Transition helpers -------------------------------- */
bool TrackDrinkingMovingSM::startDrinking() {
  if (currentState == State::TRACK) {
    currentState = State::DRINKING;
    return true;
  }
  return false; // illegal transition
}

bool TrackDrinkingMovingSM::stopDrinking() {
  if (currentState == State::DRINKING) {
    currentState = State::TRACK;
    return true;
  }
  return false;
}

bool TrackDrinkingMovingSM::startMoving() {
  if (currentState == State::TRACK) {
    currentState = State::MOVING;
    return true;
  }
  return false;
}

bool TrackDrinkingMovingSM::stopMoving() {
  if (currentState == State::MOVING) {
    currentState = State::TRACK;
    return true;
  }
  return false;
}

/* ---------- State query -------------------------------------- */
TrackDrinkingMovingSM::State TrackDrinkingMovingSM::getState() const {
  return currentState;
}

/* ---------- Debug helper ------------------------------------- */
String TrackDrinkingMovingSM::stateToString() const {
  switch (currentState) {
  case State::TRACK:
    return "TRACK";
  case State::DRINKING:
    return "DRINKING";
  case State::MOVING:
    return "MOVING";
  }
  return "UNKNOWN";
}
