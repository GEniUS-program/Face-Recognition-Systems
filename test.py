import cv2
import face_recognition
import numpy as np

# Replace 0 with filename if needed
video = cv2.VideoCapture(0)

# Initialize variables
trackers = []
example_names = ['John', 'Jane', 'Bob', 'Andrew', 'Alex', 'Emily', 'Olivia', 'Emma', 'Sophia', 'Isabella',
                 'Mia', 'Charlotte', 'Amelia', 'Harper', 'Ella', 'Abigail', 'Emily', 'Elizabeth', 'Mila', 'Ava']
bboxes = []
names = []
frame_count = 0
face_detection_interval = 15  # Detect faces every 15 frames
face_tracking_interval = 5  # Track faces every 5 frames
movement_threshold = 175  # Define a threshold for sudden movement

def create_trackers(frame): # this is where we send the frame to face_recognition to assign the correct names to the faces
    faces = face_recognition.face_locations(frame)
    global example_names, trackers
    for face, name in zip(faces, example_names):
        #if any(name in i for i in trackers):# checking if the tracker exists (only works with face recognition full - when faces get assigned correct names and not random ones)
        #    continue# 
        top, right, bottom, left = face  # Unpack the coordinates
        tracker = cv2.TrackerCSRT_create()
        tracker.init(frame, (left, top, right - left, bottom - top))  # Initialize tracker with correct format
        trackers.append([tracker, name, (left, top)])  # Store the initial position

def check_trackers(frame, bboxes=[], names=[]):
    global trackers
    new_faces = False
    bboxes = bboxes
    names = names
    if frame_count % face_detection_interval == 0:
        faces = face_recognition.face_locations(frame)
        if len(faces) > len(trackers):
            print('more faces detected than the amount of trackers')
            create_trackers(frame)
            new_faces = True

    if frame_count % face_tracking_interval == 0:
        bboxes = []
        # Update existing trackers
        for i, (tracker, name, last_position) in enumerate(trackers):
            success, bbox = tracker.update(frame)
            if success:
                bboxes.append(bbox)
                names.append(name)
                x, y, w, h = [int(v) for v in bbox]
                current_position = (x, y)

                # Calculate movement distance
                distance_moved = np.sqrt((current_position[0] - last_position[0]) ** 2 + (current_position[1] - last_position[1]) ** 2)

                # Check if the movement exceeds the threshold
                if distance_moved > movement_threshold:
                    print(f'lost tracker for {name} to sudden movement')
                    cv2.putText(frame, f"Tracker for {name} lost due to sudden movement", (100, 80 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
                    del trackers[i]  # Remove the tracker
                else:
                    # Update the last known position
                    trackers[i][2] = current_position  # Update last_position

                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            else:
                print('lost tracking for', name)
                cv2.putText(frame, f"Tracker for {name} lost", (100, 80 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
                del trackers[i]
    else:
        for (box, name) in zip(bboxes, names):
            x, y, w, h = [int(v) for v in box]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)


    return frame, bboxes, names

# Main tracking loop
while True:
    ret, frame = video.read()
    if not ret:
        break

    frame_count += 1
    frame, bboxes, names = check_trackers(frame, bboxes, names)

    # Display the frame
    cv2.imshow("MultiTracker", frame)

    # Exit if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
video.release()
cv2.destroyAllWindows()
