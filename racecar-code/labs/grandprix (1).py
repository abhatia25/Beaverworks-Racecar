"""
Copyright MIT and Harvey Mudd College
MIT License
Summer 2020

Lab 5B - LIDAR Wall Following
"""

########################################################################################
# Imports
########################################################################################

import sys
import cv2 as cv
import numpy as np

sys.path.insert(1, "../library")
import racecar_core
import racecar_utils as rc_utils
import copy
from enum import IntEnum

########################################################################################
# Global variables
########################################################################################

rc = racecar_core.create_racecar()

# Add any global variables here

MIN_CONTOUR_AREA = 30

CROP_FLOOR = ((360, 0), (rc.camera.get_height(), rc.camera.get_width() - 350))

CROP_FLOOR2 = ((360, 0), (rc.camera.get_height(), rc.camera.get_width()))

BLUE = ((90, 100, 100), (110, 255, 255))  # The HSV range for the color blue
GREEN = ((40, 50, 50), (80, 255, 255))  # The HSV range for the color green
RED = ((170, 50, 50), (10, 255, 255))  # The HSV range for the color red
PURPLE = ((130, 50, 50), (155, 255, 255))
ORANGE = ((7, 50, 50), (20, 255, 255))

contour_area = 0  # The area of contour
counter = 0
contour_center = None
image = None


ar_contour_center = None
ar_contour_area = 0

prev_distance = 0

speed = 0.0  # The current speed of the car
angle = 0.0  # The current angle of the car's wheels
COLOR_PRIORITY = (GREEN, RED, BLUE)


class State(IntEnum):
    DRIVING = 0
    TURNING = 1


class CONES_COLOR(IntEnum):
    BLUE = 0
    RED = 1
    NA = 2


BLUE_TURN = -1
RED_TURN = 1

K_P = -0.72  # PD values
K_I = -0.13
K_D = -0.23

currentIntegral = 0
lastError = 0

# Add any global variables here
turn = 0
cur_state = State.DRIVING
CONES_MIN_CONTOUR_AREA = 120
CROP_AREA = 80

CONES_RED = ((170, 50, 50), (179, 255, 255))
CONES_BLUE = ((90, 120, 50), (120, 255, 255))  # The HSV range for the color blue

contour_color = CONES_COLOR.NA
last_contour_color = CONES_COLOR.NA
contour = None

ANGLE_OFFSET = 140
STOP_DISTANCE = 41

class Mode(IntEnum):
    wallFollowing = 0
    laneFollowing = 1
    coneSlaloming = 3
    lineFollowing = 4

errorCounter = 0

cur_mode = Mode.wallFollowing
red_center = None
red_distance = 0
prev_red_distance = 0
blue_center = None
blue_distance = 0
prev_blue_distance = 0
line_tag_count = 0
line_detected = False
COLOR = ""
line_end = 0
tag_detected = False
########################################################################################
# Functions
########################################################################################

def resetVariables(mode = Mode.wallFollowing):

    

    global cur_mode

    global contour_color
    global last_contour_color
    global contour
    global contour_area
    global counter
    global contour_center
    global image
    global prev_distance
    global speed
    global angle
    global turn
    global cur_state
    global currentIntegral
    global lastError

    global ar_contour_center
    global ar_contour_area

    global red_center
    global red_distance
    global prev_red_distance
    global blue_center
    global blue_distance
    global prev_blue_distance
    global line_tag_count
    global line_detected
    global COLOR
    global line_end
    global tag_detected
    global errorCounter

    errorCounter = 0

    contour_color = CONES_COLOR.NA
    last_contour_color = CONES_COLOR.NA
    contour = None

    contour_area = 0 
    counter = 0
    contour_center = None
    image = None

    prev_distance = 0

    speed = 0.0  
    angle = 0.0  

    turn = 0
    cur_state = State.DRIVING

    currentIntegral = 0
    lastError = 0

    ar_contour_area = 0
    ar_contour_center = None

    red_center = None
    red_distance = 0
    prev_red_distance = 0
    blue_center = None
    blue_distance = 0
    prev_blue_distance = 0
    line_tag_count = 0
    line_detected = False
    line_end = 0
    tag_detected = False

    cur_mode = mode

def update_lane_contour():
    """
    Finds contours in the current color image and uses them to update contour_center
    and contour_area
    """
    global contour_center
    global contour_area
    
    imageCopy = copy.deepcopy(image)
    if imageCopy is None:
        contour_center = None
        contour_area = 0
    else:
        imageCopy = rc_utils.crop(imageCopy, CROP_FLOOR[0], CROP_FLOOR[1])

        contour = None
        purpleContours = rc_utils.find_contours(imageCopy, PURPLE[0], PURPLE[1])
        orangeContours = rc_utils.find_contours(imageCopy, ORANGE[0], ORANGE[1])

        purpleContour = rc_utils.get_largest_contour(purpleContours, MIN_CONTOUR_AREA)
        orangeContour = rc_utils.get_largest_contour(orangeContours, MIN_CONTOUR_AREA)
        if purpleContour is None and orangeContour is not None:
            contour = orangeContour
        elif orangeContour is None and purpleContour is not None:
            contour = purpleContour
        elif orangeContour is not None and purpleContour is not None:
            purpleArea = rc_utils.get_contour_area(purpleContour)
            orangeArea = rc_utils.get_contour_area(orangeContour)
            if purpleArea > orangeArea:
                contour = purpleContour
            else:
                contour = orangeContour
        else:
            contour_center = None
            contour_area = 0
            return

        contour_center = rc_utils.get_contour_center(contour)
        contour_area = rc_utils.get_contour_area(contour)

        rc_utils.draw_contour(imageCopy, contour)
        rc_utils.draw_circle(imageCopy, contour_center)

      #  rc.display.show_color_image(imageCopy)


def update_line_contour():
    """
    Finds contours in the current color image and uses them to update contour_center
    and contour_area
    """
    global contour_center
    global contour_area

    imageCopy = copy.deepcopy(image)

    if imageCopy is None:
        contour_center = None
        contour_area = 0
    else:
        # Crop the image to the floor directly in front of the car
        imageCopy = rc_utils.crop(imageCopy, CROP_FLOOR2[0], CROP_FLOOR2[1])

        # Find all of the contours of the current color
        contours = rc_utils.find_contours(imageCopy, COLOR[0], COLOR[1])

        # Select the largest contour
        contour = rc_utils.get_largest_contour(contours, MIN_CONTOUR_AREA)

        if contour is not None:
            # Calculate contour information
            contour_center = rc_utils.get_contour_center(contour)
            contour_area = rc_utils.get_contour_area(contour)

            # Draw contour onto the image
            rc_utils.draw_contour(imageCopy, contour)
            rc_utils.draw_circle(imageCopy, contour_center)

        # If no contours are found for any color, set center and area accordingly
        else:
            contour_center = None
            contour_area = 0

        # Display the image to the screen
     #   rc.display.show_color_image(image)


def update_cones_contour():
    global contour_center
    global contour_area
    global contour_color
    global contour

    imageCopy = copy.deepcopy(image)


    if imageCopy is None:
        contour_center = None
        contour_area = 0
    else:
        top_left_inclusive = (0, CROP_AREA)
        bottom_right_exclusive = (rc.camera.get_height(), rc.camera.get_width() - CROP_AREA)

        imageCopy = rc_utils.crop(imageCopy, top_left_inclusive, bottom_right_exclusive)

        redContours = rc_utils.find_contours(imageCopy, CONES_RED[0], CONES_RED[1])
        blueContours = rc_utils.find_contours(imageCopy, CONES_BLUE[0], CONES_BLUE[1])

        redContour = rc_utils.get_largest_contour(redContours, MIN_CONTOUR_AREA)
        blueContour = rc_utils.get_largest_contour(blueContours, MIN_CONTOUR_AREA)
        if redContour is None and blueContour is not None:
            contour = blueContour
            contour_color = CONES_COLOR.BLUE
        elif blueContour is None and redContour is not None:
            contour = redContour
            contour_color = CONES_COLOR.RED
        elif blueContour is not None and redContour is not None:
            redArea = rc_utils.get_contour_area(redContour)
            blueArea = rc_utils.get_contour_area(blueContour)
            if redArea > blueArea:
                contour = redContour
                contour_color = CONES_COLOR.RED
            else:
                contour = blueContour
                contour_color = CONES_COLOR.BLUE
        else:
            contour_center = None
            contour_area = 0
            contour_color = CONES_COLOR.NA

            return

        contour_center = rc_utils.get_contour_center(contour)
        contour_area = rc_utils.get_contour_area(contour)

        rc_utils.draw_contour(imageCopy, contour)
        rc_utils.draw_circle(imageCopy, contour_center)
    #    rc.display.show_color_image(imageCopy)

def update_ar_contour():
    """
    Finds contours in the current color image and uses them to update contour_center
    and contour_area
    """
    BLUE = ((100, 200, 50), (120, 255, 255))
    RED = ((0, 200, 50), (10, 255, 255))
    GREEN = ((50, 200, 50), (80, 255, 255))
    ORANGE = ((10, 50, 50), (20, 255, 255))
    PURPLE = ((130, 50, 50), (155, 255, 255))
    AR_COLOR_PRIORITY = [BLUE, RED, GREEN, ORANGE, PURPLE]
    global ar_contour_center
    global ar_contour_area
    global COLOR
    imageCopy = copy.deepcopy(image)

    if imageCopy is None:
        contour_center = None
        contour_area = 0
    else:
        # Search for each color in priority order
        for color in AR_COLOR_PRIORITY:
            # Find all of the contours of the current color
            contours = rc_utils.find_contours(imageCopy, color[0], color[1])

            # Select the largest contour
            contour = rc_utils.get_largest_contour(contours, MIN_CONTOUR_AREA)

            if contour is not None:
                COLOR = color
                # Calculate contour information
                contour_center = rc_utils.get_contour_center(contour)
                contour_area = rc_utils.get_contour_area(contour)

                # Draw contour onto the image
                rc_utils.draw_contour(imageCopy, contour)
                rc_utils.draw_circle(imageCopy, contour_center)

                break

        # If no contours are found for any color, set center and area accordingly
        else:
            contour_center = None
            contour_area = 0

        # Display the image to the screen
    #    rc.display.show_color_image(image)


def start():
    """
    This function is run once every time the start button is pressed
    """
    global prev_distance
    global counter
    # Have the car begin at a stop
    rc.drive.stop()

    scan = rc.lidar.get_samples()
    prev_distance = scan[0]

    # Have the car begin at a stop, in no_cones mode
    rc.drive.stop()
    counter = 0
    # Print start message

    resetVariables()
    print(">> Lab 5B - LIDAR Wall Following")


def follow_art_wall():
    global prev_distance
    global speed
    global angle
    global errorCounter
    

    LOOKING_ANGLE_DEGREES = 9
    LEFT_ANGLE = 321
    RIGHT_ANGLE = 39

    depth_image = rc.camera.get_depth_image()
    center_distance = rc_utils.get_pixel_average_distance(depth_image,(rc.camera.get_height() // 2 + 10, rc.camera.get_width() // 2))   

    speed = 1#rc_utils.clamp((7 - center_distance) * -0.0031, -1,1)
    scan = rc.lidar.get_samples()
    distance = rc_utils.get_lidar_average_distance(scan, LEFT_ANGLE, LOOKING_ANGLE_DEGREES)
    distance2 = rc_utils.get_lidar_average_distance(scan, RIGHT_ANGLE, LOOKING_ANGLE_DEGREES)
    dist_diff = distance2 - distance
    max_speed = 0.25
    prev_distance = scan[0]
    rc.drive.set_max_speed(max_speed)
    angle = rc_utils.clamp(dist_diff * 0.0085, -1, 1)
    
    scan = (scan - 0.01) % 1000000


    for i in range(3): 
        if rc_utils.get_lidar_average_distance(scan,-87 + i,2) > 600 or rc_utils.get_lidar_average_distance(scan,87 - i,2) > 600 and  center_distance > 30:
            distance = rc_utils.get_lidar_average_distance(scan, -7, LOOKING_ANGLE_DEGREES)
            distance2 = rc_utils.get_lidar_average_distance(scan, 7, LOOKING_ANGLE_DEGREES)
            dist_diff = distance2 - distance

            angle = rc_utils.clamp(dist_diff * 0.0008, -0.9, 0.9)
            print("active")
            break

    
    
    ids, direction, distanceToTag = get_tags()

    if ids is not None and ids[0][0] == 199 and distanceToTag < 100:
        if direction == rc_utils.Direction.LEFT:
            angle = -1
        else:
            angle = 1

    if abs(rc.physics.get_linear_acceleration()[2]) < 0.01:
        errorCounter += rc.get_delta_time()
    else:
        errorCounter = 0
    
    if errorCounter > 3:
        errorCounter = -2
    elif errorCounter < 0:
        rc.drive.set_speed_angle(-0.7, -1)
        errorCounter += rc.get_delta_time()


def cone_slalom():
    global cur_state
    global lastError
    global contour_center
    global contour_area
    global counter
    global image
    global speed
    global angle
    global turn
    global currentIntegral
    global contour_color
    global last_contour_color

    speed = 0
    angle = 0
    rc.drive.set_max_speed(0.25)


    offset_center = None
    depth_image = rc.camera.get_depth_image()

    top_left_inclusive = (0, CROP_AREA)
    bottom_right_exclusive = (rc.camera.get_height(), rc.camera.get_width() - CROP_AREA)

    depth_image = rc_utils.crop(depth_image, top_left_inclusive, bottom_right_exclusive)

    print(cur_state)

    if (cur_state == State.DRIVING):
        if contour_center is None:
            return

        if contour_color == CONES_COLOR.RED:
            offset_center = (contour_center[0], rc_utils.clamp(contour_center[1] + ANGLE_OFFSET, 0,
                                                               rc.camera.get_width() - (
                                                                           CROP_AREA * 2)))  # clamp contour_center
        else:
            offset_center = (contour_center[0], rc_utils.clamp(contour_center[1] - ANGLE_OFFSET, 0,
                                                               rc.camera.get_width() - (
                                                                           CROP_AREA * 2)))  # clamp contour_center

        contour_center_distance = rc_utils.get_pixel_average_distance(depth_image, contour_center)

        error = STOP_DISTANCE - contour_center_distance
        d = (error - lastError) * (1 / rc.get_delta_time())

        lastError = error

        currentIntegral += error * rc.get_delta_time()

        speed = rc_utils.clamp(error * K_P + d * K_D + K_I * currentIntegral, -1, 1)
        angle = rc_utils.remap_range(offset_center[1], 0, rc.camera.get_width() - (CROP_AREA * 2), -1, 1)
        if contour_center_distance < (STOP_DISTANCE + 35):
            counter = 0
            cur_state = State.TURNING
            if contour_color == CONES_COLOR.RED:
                turn = RED_TURN
                last_contour_color = CONES_COLOR.RED
            else:
                turn = BLUE_TURN
                last_contour_color = CONES_COLOR.BLUE

    elif (cur_state == State.TURNING):
        THRESHOLD = 0.501
        MAX_DISTANCE = 235
        speed = 1
        if 0 < counter < THRESHOLD:
            angle = turn
        else:
            if contour_center is None:
                angle = turn * -1
            else:
                print(rc_utils.get_pixel_average_distance(depth_image, contour_center))
                contour_center_distance = rc_utils.get_pixel_average_distance(depth_image, contour_center)

                if contour_center_distance > MAX_DISTANCE:# or contour_color == last_contour_color:
                    angle = turn * -1
                else:
                    counter = 0
                    cur_state = State.DRIVING
                    currentIntegral = 0

    counter += rc.get_delta_time()
    
def follow_lane():
    global speed
    global angle
    rc.drive.set_max_speed(0.25)
    if not contour_center is None:
        angle = rc_utils.clamp(rc_utils.remap_range(contour_center[1] + 25, 0, rc.camera.get_width() - 350, -1, 1), -1, 1)
        speed = 1


def follow_line():
    rc.drive.set_max_speed(0.25)

    global speed
    global angle
    global line_detected
    if not contour_center is None:
        angle = rc_utils.clamp(rc_utils.remap_range(contour_center[1], 0, rc.camera.get_width(), -1, 1), -1, 1)
        speed = 1
        line_detected = True
    elif contour_center is None and line_detected == False:
        speed = 1
        angle = -0.4


def get_tags():
    ar_image = rc.camera.get_color_image()
    direction = None
    distance = None
    corners, ids = rc_utils.get_ar_markers(ar_image)
    if ids is not None:
        corner = corners[0]
        direction = rc_utils.get_ar_direction(corner)
        corner = corner[0]
        target = corner[0]
        if direction == rc_utils.Direction.RIGHT:
            target = corner[2]
        distance = rc_utils.get_pixel_average_distance(rc.camera.get_depth_image(), (int(target[1]), int(target[0])))
    return ids, direction, distance


def update():
    global cur_mode
    global line_tag_count
    global COLOR_PRIORITY
    global line_end
    global angle
    global speed
    global image

    

    image = rc.camera.get_color_image()

    ids, direction, distance = get_tags()

    if ids is not None:
        prev_mode = cur_mode
        if[1] in ids and distance < 100:
            cur_mode = Mode.laneFollowing
        elif [2] in ids and distance < 150:
            cur_mode = Mode.coneSlaloming
        elif[0] in ids and distance < 150:
            update_ar_contour()
            cur_mode = Mode.lineFollowing
        elif [3] in ids and distance < 200:
            cur_mode = Mode.wallFollowing
        if not (prev_mode == cur_mode):
            resetVariables(mode = cur_mode)
        
   
    if cur_mode == Mode.wallFollowing:
        follow_art_wall()
    elif cur_mode == Mode.laneFollowing:
        update_lane_contour()
        follow_lane()
    elif cur_mode == Mode.coneSlaloming:
        update_cones_contour()
        cone_slalom()
    elif cur_mode == Mode.lineFollowing:
        update_line_contour()
        follow_line()
        if line_detected == True and contour_center is None:
            line_end += 1
        elif contour_center is not None:
            line_end = 0
        if line_end == 30:
            cur_mode = Mode.wallFollowing


    


    rc.drive.set_speed_angle(speed, angle)


    print("Mode: ", cur_mode, "Distance: ", distance)

    # first 1, second 3 UP , third 2, fourth 0, 5th 3, 6th 199



########################################################################################
# DO NOT MODIFY: Register start and update and begin execution
########################################################################################

if __name__ == "__main__":
    rc.set_start_update(start, update, None)
    rc.go()
