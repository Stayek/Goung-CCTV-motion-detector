import datetime, time 
import cv2

def createTimeStamp(frame,timestamp):
    cv2.putText(frame, timestamp.strftime("%A %d %B %Y %I:%M:%S%p"), (10, 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)



def drawBoxForMotion(contour,frame):
    (x, y, w, h) = cv2.boundingRect(contour)
    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)


def extractAllContonours(contours, SizeOfArea=700):
    # Extracts the bigger white motion detected areas 
    outGeneratedContours =[]
    for contour in contours:
        if cv2.contourArea(contour) < SizeOfArea:        
            continue
        else:
            outGeneratedContours.append(contour)
    return outGeneratedContours


        
def detectAllMotionsInFrame(prevFrame, currentFrame, thresholdVal = 20):
    diff = cv2.absdiff(prevFrame, currentFrame)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    ThreshiHold = cv2.threshold(blur, thresholdVal, 255, cv2.THRESH_BINARY)[1]
    dilated = cv2.dilate(ThreshiHold, None, iterations=3)
    contours = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]
    contours = extractAllContonours(contours)
    if(len(contours)==0):
        return None
    return contours

def gen_video_name(name, timestamp):
    return name+'_'+timestamp.strftime("%d-%m-%Y_%H-%M-%S")

