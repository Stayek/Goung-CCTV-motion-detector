import numpy as np
import cv2

with open("packages/mobileNetSSDClasses.txt", 'r') as f:
    CLASSES = [line.strip() for line in f.readlines()]

Calars = np.random.uniform(0, 255, size=(len(CLASSES), 3))
net = cv2.dnn.readNetFromCaffe("packages/MobileNetSSD_deploy.prototxt.txt",
 "packages/MobileNetSSD_deploy.caffemodel")
minimumThreshold = 0.3
blob_res = (200, 200)

def detectObjects(prevFrame,curFrame,classesNeededTofind):

    isDetected = 0
    frameH = curFrame.shape[0]
    frameW = curFrame.shape[1]

    blob = cv2.dnn.blobFromImage(cv2.resize(curFrame,blob_res ), 0.005619, blob_res)
    net.setInput(blob)
    detections = net.forward()


    for i in range(detections.shape[2]): 

        confidence = detections[0, 0, i, 2] 

        if confidence > minimumThreshold:

            classificationIndex = int(detections[0, 0, i, 1])
            if(classificationIndex in classesNeededTofind):
                box = detections[0, 0, i, 3:7] * np.array([frameW , 
                    frameH, frameW , frameH])
                (x, y, w, h) = box.astype("int")
                # display detection shape outline
                label = CLASSES[classificationIndex]
                cv2.putText(prevFrame, label, (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, Calars[classificationIndex], 2)
                cv2.rectangle(prevFrame, (x, y), 
                    (w, h), Calars[classificationIndex], 2)
                isDetected = 1

    if(isDetected): return True
    else: return False
