import cv2
import numpy as np
from facenet_pytorch import MTCNN
import torch
from time import sleep

# Replace 0 with filename if needed
video = cv2.VideoCapture('./test/1.avi')

# Initialize variables
trackers = []
example_names = ['John', 'Jane', 'Bob', 'Andrew', 'Alex', 'Emily', 'Olivia', 'Emma', 'Sophia', 'Isabella',
                 'Mia', 'Charlotte', 'Amelia', 'Harper', 'Ella', 'Abigail', 'Emily', 'Elizabeth', 'Mila', 'Ava']
bboxes = []
names = []
frame_count = 0
face_detection_interval = 15  # Detect faces every 15 frames
face_tracking_interval = 5  # Track faces every 5 frames
movement_threshold = 50  # Define a threshold for sudden movement
mtcnn = MTCNN(keep_all=True, device='cuda' if torch.cuda.is_available() else 'cpu')  # keep_all=True to detect all faces in the frame
messages = []#['message', 'frames left']

def create_trackers(frame, faces): # this is where we send the frame to face_recognition to assign the correct names to the faces

    global example_names, trackers
    trackers = []
    for face, name in zip(faces, example_names):
        #if any(name in i for i in trackers):# checking if the tracker exists (only works with face recognition full - when faces get assigned correct names and not random ones)
        #    continue# 
        top, right, bottom, left = face  # Unpack the coordinates

    # Calculate width and height of the bounding box
        width = right - left
        height = bottom - top
        if width > 0 and height > 0:
            tracker = cv2.TrackerCSRT_create()  # Create a new tracker for each face
            success = tracker.init(frame, (left, top, width, height))
            if not success:
                print("Tracker initialization failed for this bounding box.")
                trackers.append([tracker, name, (left, top)])
                messages.append([f'failed to initialize tracker for {name}', 60])
        else:
            print("Invalid bounding box dimensions.")

def check_trackers(frame, bboxes=[], names=[]):
    global trackers
    bboxes = bboxes
    names = names
    if frame_count % face_detection_interval == 0:
        set_faces = []

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        #MTCNN detection
        boxes, _ = mtcnn.detect(rgb_frame)  # Pass the RGB to MTCNN
        if boxes is not None:
            for box in boxes:
                x1, y1, x2, y2 = box
                top = int(y1)
                right = int(x2)
                bottom = int(y2)
                left = int(x1)
                set_faces.append((top, right, bottom, left))

        if len(set_faces) >= len(trackers):
            messages.append(['creating trackers based on new faces.....', 60])
            create_trackers(frame, set_faces)
            messages.append(['created trackers based on new faces', 60])

    

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
                    del trackers[i]  # Remove the tracker
                    messages.append([f'{name} moved too fast', 60])
                else:
                    # Update the last known position
                    trackers[i][2] = current_position  # Update last_position
                    messages.append([f'updated tracker for {name}', 60])
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            else:
                messages.append([f'failed to update tracker for {name}', 60])
                del trackers[i]
    else:
        for (box, name) in zip(bboxes, names):
            x, y, w, h = [int(v) for v in box]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)


    return frame, bboxes, names

fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter('your_video.avi', fourcc, 20.0, (1200, 650))


# Main tracking loop
while True:
    ret, frame = video.read()
    if not ret:
        break

    print(frame.shape)
    frame_count += 1
    frame, bboxes, names = check_trackers(frame, bboxes, names)

    for i, message in enumerate(messages):
        message[1] -= 1
        if message[1] == 0:
            messages.remove(message)
        else:
            cv2.putText(frame, message[0], (10, frame.shape[1] - 350 - 20 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(frame, f'Tracker Count: {len(trackers)}', (40, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    frame = cv2.resize(frame, (1200, 650))
    out.write(frame)
    cv2.imshow("MultiTracker", frame)
    sleep(0.033)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
video.release()
cv2.destroyAllWindows()
