import cv2

# Initialize video capture
video = cv2.VideoCapture(0)

# Read the first frame
ret, frame = video.read()
if not ret:
    print("Error reading video")
    exit()

# Create a list to store individual trackers and their IDs
trackers = []
tracker_ids = []

# Select ROIs for each object to track
print("Select ROIs for each object and press ENTER to start tracking.")
while True:
    bbox = cv2.selectROI("MultiTracker", frame, fromCenter=False)
    tracker = cv2.legacy.TrackerKCF().create()
    tracker.init(frame, bbox)
    trackers.append(tracker)
    tracker_ids.append(len(tracker_ids) + 1)  # Assign a unique ID to each tracker
    print(f"Added tracker {len(tracker_ids)} with bounding box: {bbox}")
    k = cv2.waitKey(0) & 0xFF
    if k == 13:  # Press ENTER to finish selecting ROIs
        break

# Main tracking loop
while True:
    ret, frame = video.read()
    if not ret:
        break

    # Update each tracker individually
    for i, (tracker, tracker_id) in enumerate(zip(trackers, tracker_ids)):
        success, bbox = tracker.update(frame)

        # Check if the tracker is successful
        if success:
            x, y, w, h = [int(v) for v in bbox]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"Tracker {tracker_id}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
        else:
            # If the tracker fails, mark it as failed
            cv2.putText(frame, f"Tracker {tracker_id} failed", (100, 80 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
            print(f"Tracker {tracker_id} failed!")

    # Display the frame
    cv2.imshow("MultiTracker", frame)

    # Exit if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
video.release()
cv2.destroyAllWindows()