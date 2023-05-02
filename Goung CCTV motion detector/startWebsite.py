from packages.motionDetection import *
from packages.objectDetection import *
from flask import (Flask, render_template, Response,request, redirect, send_file, jsonify, after_this_request)
from flask_sqlalchemy import SQLAlchemy
import os 
import sys


app = Flask(__name__,static_folder='static')


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///records.db'

app.config["SQLAlchemy_TRACK_MODIFICATIONS"] = False

app.config['SECRET_KEY'] = "ok"
db = SQLAlchemy(app)

# Classes


class configUsr(db.Model):
	id = db.Column(db.Integer,primary_key = True)
	isDetectPerson= db.Column(db.Boolean)
	isDetectVehicle = db.Column(db.Boolean)
	def __init__(self,person):
		self.isDetectPerson= person 


# Recorded Output Video 

FPSVid = 30
#.AVI = 'XVID' 
formatOfVid = 'mp4'
fourcc = cv2.VideoWriter_fourcc(*"H264") # this one is MP4 encode

ResolutionVid = (854,480)
recording = False


isOutputeGenerated = False
initializeFrames = True

camera = cv2.VideoCapture(0) 
# camera = cv2.VideoCapture('static/test/testVideo.mp4')
nameOfCam = "camera"
prevFrame = None
curFrame = None

# Other settings
curVid = "data:,"
curVidID = -1
isOutputGenereated = False
canSendRefreshStat = False

recordingStoppedTime = None
time_after_record_ended = 5
isTimerStart = False


isDetectPerson= False
isDetectVehicle = False

outGenerator = None


# Methods

def generateVid(database, nameOfCam, timestamp):
	global isOutputeGenerated, outGenerator
	if isOutputeGenerated == False:
		outGenerator = cv2.VideoWriter(f"static/{gen_video_name(nameOfCam,timestamp)}.{formatOfVid}", fourcc, FPSVid, ResolutionVid,0)
		isOutputeGenerated = True
		recordNew = Record(gen_video_name(nameOfCam,timestamp))
		database.session.add(recordNew)
		database.session.commit()
		buffer = cv2.imencode('.jpg', cv2.resize(curFrame.copy(),(854,480)))[1]
		img_frame = buffer.tobytes()
		
	frameOutput = curFrame.copy()
	createTimeStamp(frameOutput,timestamp)
	frameOutput = cv2.resize(frameOutput, ResolutionVid)
	outGenerator.write(frameOutput)


def detectMotionDetections():
	global curFrame, prevFrame, canSendRefreshStat, recording, isTimerStart, recordingStoppedTime, isOutputeGenerated
	
	prevFrame = curFrame
	isCamWork, curFrame = camera.read()
	if not isCamWork:
		outGenerator.release() 
		return False 
				
	timestamp = datetime.datetime.now()
	createTimeStamp(curFrame, timestamp)

	detected = False
	if isDetectPerson and isDetectVehicle:
		detected = detectObjects(prevFrame,curFrame,(7,15)) 
	elif isDetectVehicle:
		detected = detectObjects(prevFrame,curFrame,(7,))
	elif isDetectPerson:
		detected = detectObjects(prevFrame,curFrame,(15,))
	else:
		contours = detectAllMotionsInFrame(prevFrame, curFrame)
		detected = (0,1)[contours is not None]

	if detected:
		if recording:
			isTimerStart = False
		else:
			recording = True
			print("START",file=sys.stderr)
		if not isDetectPerson or isDetectVehicle:
			for contour in contours:
				drawBoxForMotion(contour, prevFrame)

	elif recording:
		if isTimerStart:
			if time.time() - recordingStoppedTime >= time_after_record_ended:
				recording = False
				isOutputeGenerated = False
				isTimerStart = False
				outGenerator.release() # Very important Without release recorded footage wont be saved
				print("STOP",file=sys.stderr)
				canSendRefreshStat = True
		else:
			isTimerStart = True
			recordingStoppedTime = time.time()
	

	if recording: 
		generateVid(db,nameOfCam, timestamp)
	return True


def generatingFrames(): 
	global isOutputGenereated, prevFrame, curFrame, initializeFrames
	if initializeFrames:	
		prevFrame = camera.read(0)[1]
		curFrame = prevFrame
		initializeFrames = False
	while True:
		
		if not detectMotionDetections():
			break
		
		buffer = cv2.imencode('.jpg', prevFrame)[1] #make frame to jpg
		img_frame = buffer.tobytes()
		
		yield (b'--frame\r\n'
			b'Content-Type: image/jpeg\r\n\r\n' + img_frame + b'\r\n') # starts from

def generatingThumbnial(nameOfVid): 
	video = cv2.VideoCapture(f'static/{nameOfVid}.mp4')
	if video.isOpened():
		video.set(2,0.5); 
		frame = video.retrieve()[1]  
		video.release()
		frame = cv2.resize(frame, (52,30))
		buffer = cv2.imencode('.jpg', frame)[1]
		frame = buffer.tobytes()
		yield (b'--frame\r\n'
			b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  
	else:
		video.release()
		yield(b'--frame\r\n')

def checkBoxValue(checkbox):
	return (0,1)[request.form.get(checkbox)=="on"]

# routes

@app.route('/', methods=["POST","GET"])
def index():
	global curVid, canSendRefreshStat

	canSendRefreshStat = False

	videosRecorded = Record.query.order_by(Record.id.desc()).all()

	return render_template('index.html',nameOfVid = curVid, 
		curVidID=curVidID, formatOfVid = formatOfVid,videosRecorded = videosRecorded,
		isDetectPerson=isDetectPerson, isDetectVehicle=isDetectVehicle)

@app.route('/download/<nameOfVid>,<formatOfVid>')
def download_video (nameOfVid,formatOfVid):
    path = f"static/{nameOfVid}.{formatOfVid}"
    return send_file(path, as_attachment=True)

@app.route('/deleteVid/<VideoID>')
def deleteVid(VideoID):
	global curVid

	if os.path.isfile(f'static/{curVid}.{formatOfVid}'):
		os.remove(f'static/{curVid}.{formatOfVid}')
	# delete from db
	recordOfVid = Record.query.get_or_404(VideoID)
	db.session.delete(recordOfVid)
	db.session.commit()
	curVid = "data:,"
	return redirect("/")


@app.route('/updateCfg/', methods=['POST'])
def updateCfg():
	global isDetectPerson, isDetectVehicle
	
	if request.method == "POST":
		isDetectPerson= checkBoxValue("isDetectPerson")
		isDetectVehicle = checkBoxValue("isDetectVehicle")

		user = configUsr.query.get(1)
		user.isDetectPerson= isDetectPerson
		user.isDetectVehicle = isDetectVehicle
		db.session.commit()
	return redirect('/')


@app.route('/videoPlay/<nameOfVid>,<VideoID>')
def videoPlay(nameOfVid,VideoID):
	global curVid, curVidID
	curVid = nameOfVid
	curVidID = VideoID
	return redirect("/")


@app.route('/liveStream')
def liveStream():
	return Response(generatingFrames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/pageRefresh', methods=['GET'])
def pageRefresh():
    @after_this_request
    def add_header(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response  
    
    return jsonify(canSendRefreshStat) 
	
@app.route('/receiveThumb/<nameOfVid>')
def receiveThumb(nameOfVid):
	return Response(generatingThumbnial(nameOfVid), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
	db.create_all() 
	# initialize the user config record if no exists
	if db.session.query(configUsr.isDetectPerson).count() == 0:
		configUsr = configUsr(True)
		db.session.add(configUsr)
		db.session.commit()
	user_conf = configUsr.query.get(1)
	isDetectVehicle = user_conf.isDetectVehicle
	isDetectPerson= user_conf.isDetectPerson
	app.run(debug=True)
