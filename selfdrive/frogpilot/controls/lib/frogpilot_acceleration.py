from openpilot.common.numpy_fast import clip, interp

from openpilot.selfdrive.car.interfaces import ACCEL_MIN, ACCEL_MAX
from openpilot.selfdrive.controls.lib.longitudinal_planner import A_CRUISE_MIN, get_max_accel

from openpilot.selfdrive.frogpilot.controls.lib.frogpilot_variables import CITY_SPEED_LIMIT, CRUISING_SPEED, get_max_allowed_accel

A_CRUISE_MIN_ECO = A_CRUISE_MIN / 4
A_CRUISE_MIN_SPORT = A_CRUISE_MIN / 2

                       # MPH = [ 0.,  11,  22,  34,  45,  56,  89]
A_CRUISE_MAX_BP_CUSTOM =       [ 0.,  5., 10., 15., 20., 25., 40.]
A_CRUISE_MAX_VALS_ECO =        [1.4, 1.3, 1.2, 1.1, 1.0, 0.8, 0.6]
A_CRUISE_MAX_VALS_SPORT =      [3.0, 2.5, 2.0, 1.5, 1.0, 0.8, 0.6]
A_CRUISE_MAX_VALS_SPORT_PLUS = [4.0, 3.5, 3.0, 2.0, 1.0, 0.8, 0.6]

def get_max_accel_eco(v_ego):
  return interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, A_CRUISE_MAX_VALS_ECO)

def get_max_accel_sport(v_ego):
  return interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, A_CRUISE_MAX_VALS_SPORT)

def get_max_accel_sport_plus(v_ego):
  return interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, A_CRUISE_MAX_VALS_SPORT_PLUS)

def get_max_accel_ramp_off(max_accel, v_cruise, v_ego):
  return interp(v_ego, [0., v_cruise * 0.6, v_cruise * 0.8, v_cruise], [max_accel, max_accel, max_accel / 2, max_accel / 4])

class FrogPilotAcceleration:
  def __init__(self, FrogPilotPlanner):
    self.frogpilot_planner = FrogPilotPlanner

    self.acceleration_jerk = 0
    self.base_acceleration_jerk = 0
    self.base_speed_jerk = 0
    self.danger_jerk = 0
    self.max_accel = 0
    self.min_accel = 0
    self.safe_obstacle_distance = 0
    self.safe_obstacle_distance_stock = 0
    self.speed_jerk = 0
    self.stopped_equivalence_factor = 0
    self.t_follow = 0

  def update(self, controlsState, frogpilotCarState, v_cruise, v_ego, frogpilot_toggles):
    eco_gear = frogpilotCarState.ecoGear
    sport_gear = frogpilotCarState.sportGear

    if frogpilotCarState.trafficModeActive:
      self.max_accel = get_max_accel(v_ego)
    elif frogpilot_toggles.map_acceleration and (eco_gear or sport_gear):
      if eco_gear:
        self.max_accel = get_max_accel_eco(v_ego)
      else:
        if frogpilot_toggles.acceleration_profile == 3:
          self.max_accel = get_max_accel_sport_plus(v_ego)
        else:
          self.max_accel = get_max_accel_sport(v_ego)
    else:
      if frogpilot_toggles.acceleration_profile == 1:
        self.max_accel = get_max_accel_eco(v_ego)
      elif frogpilot_toggles.acceleration_profile == 2:
        self.max_accel = get_max_accel_sport(v_ego)
      elif frogpilot_toggles.acceleration_profile == 3:
        self.max_accel = get_max_accel_sport_plus(v_ego)
      elif controlsState.experimentalMode:
        self.max_accel = ACCEL_MAX
      else:
        self.max_accel = get_max_accel(v_ego)

    if frogpilot_toggles.human_acceleration:
      if self.frogpilot_planner.tracking_lead and self.frogpilot_planner.lead_one.dRel < CITY_SPEED_LIMIT * 2 and not frogpilotCarState.trafficModeActive:
        self.max_accel = clip(self.frogpilot_planner.lead_one.aLeadK, get_max_accel_sport_plus(v_ego), get_max_allowed_accel(v_ego))
      self.max_accel = get_max_accel_ramp_off(self.max_accel, self.frogpilot_planner.v_cruise, v_ego)

    if controlsState.experimentalMode:
      self.min_accel = ACCEL_MIN
    elif min(self.frogpilot_planner.frogpilot_vcruise.mtsc_target, self.frogpilot_planner.frogpilot_vcruise.vtsc_target) < v_cruise:
      self.min_accel = A_CRUISE_MIN
    elif frogpilot_toggles.map_deceleration and (eco_gear or sport_gear):
      if eco_gear:
        self.min_accel = A_CRUISE_MIN_ECO
      else:
        self.min_accel = A_CRUISE_MIN_SPORT
    else:
      if frogpilot_toggles.deceleration_profile == 1:
        self.min_accel = A_CRUISE_MIN_ECO
      elif frogpilot_toggles.deceleration_profile == 2:
        self.min_accel = A_CRUISE_MIN_SPORT
      else:
        self.min_accel = A_CRUISE_MIN