import os
import time
import cv2
from django.conf import settings
import numpy as np

# this is the dict for a specific optic sheet and its corresponding template paths
horizontal_alpha_options = {5: 'A', 4:'B', 3:'C', 2:'D', 1:'E'}
vertical_numeric_options = {1: '1', 2:'2', 3:'3', 4:'4', 5:'5', 6:'6', 7:'7', 8:'8', 9:'9', 0:'0'}

def process_uploaded_image(image_path, optic_name):
    start_time = time.time()
    
    optic_2000 = {'turkish': ('turkish_1.jpg', 'turkish_2.jpg', 'lower', 'not lower', False, 'horizontal', 'alphabetic',40), 
              'social_sciences': ('social_sciences_1.jpg', 'maths_2.jpg', 'lower', 'lower', False, 'horizontal', 'alphabetic', 46),  
              'maths': ('maths_1.jpg', 'maths_2.jpg', 'lower', 'lower', False,'horizontal', 'alphabetic', 40), 
              'fen_sciences': ('fen_sciences_1.jpg', 'fen_sciences_2.jpg', 'lower', 'not lower', False,'horizontal', 'alphabetic', 40),
              'student_number': ('student_num_1.jpg', 'student_num_2.jpg', 'lower', 'not lower', True, 'vertical', 'numeric', 5), 
              'book_type': ('book_type_1.jpg', 'book_type_2.jpg', 'lower', 'lower', False, 'special', 'alphabetic', 2), 
              'exam_type': ('exam_type_1.jpg', 'exam_type_2.jpg', 'lower', 'lower', False, 'special', 'alphabetic', 2)}

    #this will be a value returned from the client side which will determine the specific dict to use 
    if optic_name == 'optic_2000':
        optic_dict = optic_2000

    image_path = os.path.join(settings.MEDIA_ROOT, image_path)
    # read the image user uploaded
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    # starting from here finds the 4 points of the biggest rectangle and straightens the image 
    def order_points(pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect

    edges = cv2.Canny(image, 50,200, apertureSize=7, L2gradient=True)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    paper_contour = contours[0]

    epsilon = 0.02 * cv2.arcLength(paper_contour, True)
    approx = cv2.approxPolyDP(paper_contour, epsilon, True)

    if len(approx) != 4:
        print("Couldn't find a rectangular paper contour.")
        return None

    points = approx.reshape(4, 2)

    # Order the points
    rect = order_points(points)
    print('rect', rect)
    (tl, tr, br, bl) = rect

    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")


    M = cv2.getPerspectiveTransform(rect, dst)

    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

    # here the image is resized and blurred
    # should check if the image is higher or lower than the 600 by 800 size. interpolation method will change based on that.
    image =  cv2.resize(warped, (600, 800), interpolation=cv2.INTER_AREA)  # INTER_AREA is better for bigger to smaller.
    image = cv2.GaussianBlur(image, (3,3), 0)

    # 85 percent similarity for template matching
    threshold = 0.85

    # match the circle template, get all the filled circle coordinates
    filled_circle_template = os.path.join(settings.BASE_DIR, 'media', 'templates', optic_name, 'filled_circle_template.jpg')
    circle_template = cv2.imread(filled_circle_template, cv2.IMREAD_GRAYSCALE)
    circle_template_matching_result = cv2.matchTemplate(image, circle_template, cv2.TM_CCOEFF_NORMED)
    circle_template_locations = np.where(circle_template_matching_result >= threshold) 
    circle_template_locations = list(zip(*circle_template_locations[::-1]))
    print('circle_template_locations', circle_template_locations)
    all_results = {}

    for name, template_image_paths in optic_dict.items():
        print("\nSTARTING: ", name)
        template_image_1_path = os.path.join(settings.BASE_DIR, 'media', 'templates', optic_name, template_image_paths[0])
        template_image_2_path = os.path.join(settings.BASE_DIR, 'media', 'templates', optic_name, template_image_paths[1])

    
        template_image_1 = cv2.imread(template_image_1_path, cv2.IMREAD_GRAYSCALE)
        template_image_2 = cv2.imread(template_image_2_path, cv2.IMREAD_GRAYSCALE)
        template_1_lower_Y = template_image_paths[2]
        template_2_lower_Y = template_image_paths[3]
        minus_one_circle = template_image_paths[4]
        options_direction = template_image_paths[5]
        option_type = template_image_paths[6]
        nums_questions = template_image_paths[7]

        circle_shape = circle_template.shape

        template_matching_result_1 = cv2.matchTemplate(image, template_image_1, cv2.TM_CCOEFF_NORMED)
        template_matching_result_2 = cv2.matchTemplate(image, template_image_2, cv2.TM_CCOEFF_NORMED)

        template_1_locations = np.where(template_matching_result_1 >= threshold)
        template_2_locations = np.where(template_matching_result_2 >= threshold)

        print('template_1_locations', template_1_locations)
        print('template_2_locations', template_2_locations)

        template_1_locations = list(zip(*template_1_locations[::-1]))
        template_2_locations = list(zip(*template_2_locations[::-1]))

        print('template_1_locations after zip', template_1_locations)
        print('template_2_locations after zip', template_2_locations)

        # get the first location, ignore the repeats. it should only find one. can be repeats with few pixels 
        # shifted to the right or down. should check if this is the case or there is another match. could cause error.
        if len(template_1_locations) >= 1:
            template_1_location = template_1_locations[0]
        else:
            print('TEMPLATE 1 COULD NOT BE FOUND. SKIPPING')
            continue

        if len(template_2_locations) >= 1:
            template_2_location = template_2_locations[0]
        else:
            print('TEMPLATE 2 COULD NOT BE FOUND. SKIPPING')
            continue

        print('template_1_location', template_1_location)
        print('template_2_location', template_2_location)

        x_bounds = [template_1_location[0] ,template_1_location[0] + template_image_1.shape[1]]
        y_bounds = [template_1_location[1] + template_image_1.shape[0], None]

        if template_2_lower_Y == 'lower':
            y_bounds[1] = template_2_location[1] + template_image_2.shape[0]
        else:
            y_bounds[1] = template_2_location[1]

        all_circle_coordinates_list = []
        for circle_coordinates in circle_template_locations:

            # this is the bounds for the circles we want to find inside of
            if circle_coordinates[0] >= x_bounds[0] and circle_coordinates[0] + circle_template.shape[1] <= x_bounds[1] and circle_coordinates[1] >= y_bounds[0] and circle_coordinates[1] + circle_template.shape[0] <= y_bounds[1]:
                
                # store the coordinates in a list to process them
                all_circle_coordinates_list.append(circle_coordinates)

                # draw the rectangle around the found filled circle
                cv2.rectangle(image, circle_coordinates, (circle_coordinates[0] + circle_template.shape[1], circle_coordinates[1] + circle_template.shape[0]), (0, 0, 255), 2)

        print('all_circle_coordinates_list', all_circle_coordinates_list)
        print('len(all_circle_coordinates_list)', len(all_circle_coordinates_list))

        # check if any circle is found
        if len(all_circle_coordinates_list) == 0:
            print('NO CIRCLES FOUND FOR THE ' + name)
            continue
        
        prev = all_circle_coordinates_list[0]
        temp = []
        temp.append(prev)
        for i in range(1, len(all_circle_coordinates_list)):
            circle_coordinate = all_circle_coordinates_list[i]
            if circle_coordinate[1] <= prev[1] + 5 and circle_coordinate[1] >= prev[1] -5 and circle_coordinate[0] <= prev[0] + 5 and circle_coordinate[0] >= prev[0] -5:
                continue
            
            temp.append(circle_coordinate)
            prev = all_circle_coordinates_list[i]

        all_circle_coordinates_list = temp
        print('all_circle_coordinates_list after removing duplicates', all_circle_coordinates_list)

        if options_direction == 'horizontal':
            result = horizontal_options(option_type= option_type, all_circle_coordinates_list = all_circle_coordinates_list, 
                                        x_bounds = x_bounds, y_bounds=y_bounds, minus_one_circle = minus_one_circle, circle_shape=circle_shape, option_direction=None, 
                                        nums_questions=nums_questions)
            all_results[name] = result
            print('result with horizontal options', result)
            continue

        if options_direction == 'vertical':
            result = vertical_options(option_type= option_type, all_circle_coordinates_list = all_circle_coordinates_list, 
                                    x_bounds = x_bounds, y_bounds=y_bounds, minus_one_circle = minus_one_circle, 
                                    circle_shape=circle_shape, option_direction=None, nums_questions=nums_questions)
            print('result with vertical options', result)
            all_results[name] = result
            continue

        if name == 'exam_type':
            options = ['TYT', 'AYT']
            option_divides = [2]
            option_direction = 'lower_Y'
        elif name == 'book_type':
            options = ['A', 'B']
            option_divides = [8]
            option_direction = 'right_X'

        if options_direction == 'special':
            result = special_options(all_circle_coordinates_list=all_circle_coordinates_list, x_bounds=x_bounds, y_bounds=y_bounds, 
                                    circle_shape=circle_shape, option_direction=option_direction, options=options, 
                                    option_divides=option_divides)
            print('result with special options', result)
            all_results[name] = result
            continue
    
    end_time = time.time()
    print('time taken', end_time - start_time)
    return all_results


# should add option_direction. currently looks only to the top y bound to find the option choices
def vertical_options(option_type, all_circle_coordinates_list, x_bounds, y_bounds, minus_one_circle, circle_shape, option_direction, nums_questions):
    dict_to_use = {1: '1', 2:'2', 3:'3', 4:'4', 5:'5', 6:'6', 7:'7', 8:'8', 9:'9', 0:'0'}
    if option_type == 'numeric':
        dict_to_use = {1: '1', 2:'2', 3:'3', 4:'4', 5:'5', 6:'6', 7:'7', 8:'8', 9:'9', 0:'0'}

    results = []
    count = 1
    all_circle_coordinates_list = sorted(all_circle_coordinates_list, key=lambda x: x[0])

    # find if it starts with empty questions and how many
    if all_circle_coordinates_list[0][0] <= x_bounds[0] + (circle_shape[1] // 2):
        pass
    else:
        x_axis_difference = all_circle_coordinates_list[0][0] - (x_bounds[0])

        num_of_unanswered_questions = (x_axis_difference // circle_shape[1]) 
        for _ in range(0, num_of_unanswered_questions):
            results.append([count,  "EMPTY"])
            count += 1
        print('NUMBER OF EMPTY QUESTIONS FOUND UNTIL THE FIRST CIRCLE: ' + str(num_of_unanswered_questions))


    prev = all_circle_coordinates_list[0]
    y_axis_difference = prev[1] - y_bounds[0]
    circles_to_top = y_axis_difference // circle_shape[0]
    print(circles_to_top)
    if minus_one_circle == True:
        circles_to_top -= 1
    if circles_to_top in dict_to_use:
        results.append([count, dict_to_use[circles_to_top]])
        count += 1
    
    for i in range(1, len(all_circle_coordinates_list)):
        circle_coordinate = all_circle_coordinates_list[i]

        if (circle_coordinate[0] <= prev[0] + (circle_shape[1] // 2) and circle_coordinate[0] >= prev[0] - (circle_shape[1] // 2)):
            print('MULTIPLE CIRCLES FOUND FOR THE SAME X COORDINATE: ' + str(circle_coordinate[0]))
            continue
        elif (circle_coordinate[0] > prev[0] + circle_shape[1] + (circle_shape[1] // 2)):
            print('EMPTY OPTION LINE FOUND: ' + str(circle_coordinate[0]))
            x_axis_difference = circle_coordinate[0] - (prev[0] + circle_shape[1])

            num_of_unanswered_questions = (x_axis_difference // 12)

            for _ in range(0, num_of_unanswered_questions):
                results.append([count,  "EMPTY"])
                count += 1

            print('NUMBER OF EMPTY QUESTIONS FOUND UNTIL THE NEXT CIRCLE: ' + str(num_of_unanswered_questions))
        
        y_axis_difference = circle_coordinate[1] - y_bounds[0]

        circles_to_top = y_axis_difference // 12

        if minus_one_circle == True:
            circles_to_top -= 1

        if circles_to_top in dict_to_use:
            results.append([count, dict_to_use[circles_to_top]])
            count += 1

        prev = circle_coordinate
    
    if len(results) < nums_questions:
        for _ in range(0, (nums_questions - len(results))):
            results.append([count, "EMPTY"])
            count += 1
            
    return results

# should add option_direction. currently only looks to the right x bound to find the option choices
def horizontal_options(option_type, all_circle_coordinates_list, x_bounds, y_bounds, minus_one_circle, circle_shape, option_direction, nums_questions):
    dict_to_use = {}
    if option_type == 'alphabetic':
        dict_to_use = {5: 'A', 4:'B', 3:'C', 2:'D', 1:'E'}

    results = []
    count = 1

    if all_circle_coordinates_list[0][1] <= y_bounds[0] + (circle_shape[0] // 2):
        pass
    else:
        y_axis_difference = all_circle_coordinates_list[0][1] - (y_bounds[0])

        num_of_unanswered_questions = (y_axis_difference // circle_shape[0]) 
        for _ in range(0, num_of_unanswered_questions):
            results.append([count,  "EMPTY"])
            count += 1
        print('NUMBER OF EMPTY QUESTIONS FOUND UNTIL THE FIRST CIRCLE: ' + str(num_of_unanswered_questions))

    prev = all_circle_coordinates_list[0]
    x_axis_difference = x_bounds[1] - prev[0]
    circles_to_right = x_axis_difference // circle_shape[1]

    if minus_one_circle == True:
        circles_to_right -= 1

    if circles_to_right in dict_to_use:
        results.append([count, dict_to_use[circles_to_right]])
        count += 1
    

    for i in range(1, len(all_circle_coordinates_list)):
        circle_coordinate = all_circle_coordinates_list[i]

        if (circle_coordinate[1] <= prev[1] + (circle_shape[0] // 2) and circle_coordinate[1] >= prev[1] - (circle_shape[0] // 2)):
            print('MULTIPLE CIRCLES FOUND FOR THE SAME Y COORDINATE: ' + str(circle_coordinate[1]))
            continue
        elif (circle_coordinate[1] > prev[1] + circle_shape[0] + (circle_shape[0] // 2)):
            print('EMPTY OPTION LINE FOUND: ' + str(circle_coordinate[1]))
            y_axis_difference = circle_coordinate[1] - (prev[1] + circle_shape[0])

            num_of_unanswered_questions = (y_axis_difference // 12)

            for _ in range(0, num_of_unanswered_questions):
                results.append([count,  "EMPTY"])
                count += 1

            print('NUMBER OF EMPTY QUESTIONS FOUND UNTIL THE NEXT CIRCLE: ' + str(num_of_unanswered_questions))
        
        x_axis_difference = x_bounds[1] - circle_coordinate[0]

        circles_to_right = x_axis_difference // 12

        if minus_one_circle == True:
            circles_to_right -= 1

        if circles_to_right in dict_to_use:
            results.append([count, dict_to_use[circles_to_right]])
            count += 1

        prev = circle_coordinate
    
    if len(results) < nums_questions:
        for _ in range(0, (nums_questions - len(results))):
            results.append([count, "EMPTY"])
            count += 1

    return results


def special_options(all_circle_coordinates_list, x_bounds, y_bounds, circle_shape, option_direction, options, option_divides): 
    circle_coordinate  = all_circle_coordinates_list[0]
    print('COORDINATE: ' + str(circle_coordinate))
    print('X BOUNDS: ' + str(x_bounds))
    print('Y BOUNDS: ' + str(y_bounds))

    direction_difference = None
    if option_direction == 'right_X':
        direction_difference  = x_bounds[1] - circle_coordinate[0]
        nums_options_to_direction = direction_difference // circle_shape[1]
    elif option_direction == 'left_X':
        direction_difference = circle_coordinate[0] - x_bounds[0]
        nums_options_to_direction = direction_difference // circle_shape[1]
    elif option_direction == 'upper_Y':
        direction_difference  = circle_coordinate[1] - y_bounds[0]
        nums_options_to_direction = direction_difference // circle_shape[0]
    elif option_direction == 'lower_Y':
        direction_difference = y_bounds[1] - circle_coordinate[1]
        nums_options_to_direction = direction_difference // circle_shape[0] 
    
    print('DIRECTION DIFFERENCE: ' + str(direction_difference))
    print('NUMS OPTIONS TO DIRECTION: ' + str(nums_options_to_direction))
    options = options[::-1]
    print('OPTIONS: ' + str(options))
    result = None
    option_divides = option_divides[::-1]
    print('OPTION DIVIDES: ' + str(option_divides))
    i = 0
    for divide in option_divides:
        if nums_options_to_direction < divide:
            result = options[i]
            break
        else:
            result = options[i+1]
        i += 1 

    return result


