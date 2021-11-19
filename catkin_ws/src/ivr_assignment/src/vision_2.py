#!/usr/bin/env python3

import sys

import cv2
import numpy as np
import rospy
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image
from std_msgs.msg import Float64
from std_msgs.msg import Float64MultiArray


class vision_2:
    def __init__(self):
        rospy.init_node("vision_2", anonymous=True)

        # initialize the bridge between openCV and ROS
        self.bridge = CvBridge()
        self.initialiseSubscribers()
        self.initialisePublishers()
        self.initaliseMessageObjects()
        self.initialiseBlobCentres()


    def initialiseSubscribers(self):
        self.image_sub1 = rospy.Subscriber("/camera1/robot/image_raw", Image, self.callback1)
        self.image_sub2 = rospy.Subscriber("/camera2/robot/image_raw", Image, self.callback2)

    def initialisePublishers(self):
        self.joint1Pub = rospy.Publisher("joint_angle_1", Float64, queue_size=10)
        self.joint3Pub = rospy.Publisher("joint_angle_3", Float64, queue_size=10)
        self.joint4Pub = rospy.Publisher("joint_angle_4", Float64, queue_size=10)

        self.redCenterPub = rospy.Publisher("red_center", Float64MultiArray, queue_size=10)
        self.greenCenterPub = rospy.Publisher("green_center", Float64MultiArray, queue_size=10)
        self.blueCenterPub = rospy.Publisher("blue_center", Float64MultiArray, queue_size=10)
        self.yellowCenterPub = rospy.Publisher("yellow_center", Float64MultiArray, queue_size=10)

        self.vectorYBPub = rospy.Publisher("vector_yb", Float64MultiArray, queue_size=10)
        self.vectorYBtoBRPub = rospy.Publisher("vector_yb_br", Float64MultiArray, queue_size=10)

    # required so very first callback doesn't fail
    def initialiseBlobCentres(self):
        self.greenC1 = np.array([])
        self.redC1 = np.array([])
        self.blueC1 = np.array([])
        self.yellowC1 = np.array([])

    def initaliseMessageObjects(self):
        self.joint1 = Float64()
        self.joint3 = Float64()
        self.joint4 = Float64()

        self.redMsg = Float64MultiArray()
        self.greenMsg = Float64MultiArray()
        self.blueMsg = Float64MultiArray()
        self.yellowMsg = Float64MultiArray()

        self.vectorYBMsg = Float64MultiArray()
        self.vectorYBtoBRMSg = Float64MultiArray()

    def publishangles(self):
        # Publish the results
        try:
            self.joint1Pub.publish(self.joint1)
            self.joint3Pub.publish(self.joint3)
            self.joint4Pub.publish(self.joint4)
        except CvBridgeError as e:
            print(e)

    def publishCentresAndVectors(self):
        self.redMsg.data = (self.finalRedCenter/500.0).tolist()
        self.blueMsg.data = (self.finalBlueCenter/500.0).tolist()
        self.yellowMsg.data = (self.finalYellowCenter/500.0).tolist()
        self.greenMsg.data = (self.originPoint/500.0).tolist()

        self.vectorYBMsg.data = (self.vectorYB/500.0).tolist()
        self.vectorYBtoBRMSg.data = ((self.vectorYB - self.vectorBR)/500.0).tolist()

        try:
            self.redCenterPub.publish(self.redMsg)
            self.blueCenterPub.publish(self.blueMsg)
            self.yellowCenterPub.publish(self.yellowMsg)
            self.greenCenterPub.publish(self.greenMsg)

            self.vectorYBPub.publish(self.vectorYBMsg)
            self.vectorYBtoBRPub.publish(self.vectorYBtoBRMSg)
        except CvBridgeError as e:
            print(e)


    def getCentre(self, img, mask):
        cimg = cv2.bitwise_and(img, img, mask = mask)
        gray = cv2.cvtColor(cimg, cv2.COLOR_BGR2GRAY)
        #docstring of HoughCircles: HoughCircles(image, method, dp, minDist[, circles[, param1[, param2[, minRadius[, maxRadius]]]]]) -> circles
        for i in range(10, 1, -1):
            circles = cv2.HoughCircles(gray,cv2.HOUGH_GRADIENT,1,20,
                                       param1=40, param2=i, minRadius=0, maxRadius=20)
            if (circles is not None):
                circles = np.uint16(np.around(circles))
                return np.array([circles[0][0][0], -circles[0][0][1]])
            return np.array([])
            
    def findAllPoints(self, img):
        redMask = cv2.inRange(img, np.array([0, 0, 20]), np.array([20, 20, 255]))
        greenMask = cv2.inRange(img, np.array([0, 20, 0]), np.array([20, 255, 20]))
        blueMask = cv2.inRange(img, np.array([10, 0, 0]), np.array([255, 20, 20]))
        yellowMask = cv2.inRange(img, np.array([0, 10, 10]), np.array([0, 255, 255]))

        redCentre = self.getCentre(img, redMask)
        greenCentre = self.getCentre(img, greenMask)
        blueCentre = self.getCentre(img, blueMask)
        yellowCentre = self.getCentre(img, yellowMask)
        return redCentre, greenCentre, blueCentre, yellowCentre

    def callback1(self, data):
        # Receive the image
        try:
            self.cv_image1 = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError as e:
            print(e)
        self.redC1, self.greenC1, self.blueC1, self.yellowC1 = self.findAllPoints(self.cv_image1)

    def callback2(self, data):
        # Receive the image
        try:
            self.cv_image2 = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError as e:
            print(e)
        self.redC2, self.greenC2, self.blueC2, self.yellowC2 = self.findAllPoints(self.cv_image2)
        self.combinecenters()
        self.determinejointangles()
        self.publishangles()

    def determinejointangles(self):
        self.vectorYB = self.finalBlueCenter - self.finalYellowCenter
        self.vectorBR = self.finalRedCenter - self.finalBlueCenter

        vecjoint1 = np.array([-self.vectorYB[0], -self.vectorYB[1]])  # y axis also appears to be flipped from camera perspective
        vecjoint2 = np.array([-self.vectorYB[1], self.vectorYB[2]])  # y axis also appears to be flipped from camera perspective
        vecjoint4 = np.array([-self.vectorBR[1], self.vectorBR[2]])
        vecjoint3 = np.array([self.pythagoras(self.vectorYB[0], self.vectorYB[1]), self.vectorBR[2]])
        yUnitVector = np.array([0, -1])  # z axis is flipped

        self.joint1.data = self.angleBetweenVectors(yUnitVector, vecjoint1)
        self.joint3.data = self.angleBetweenVectors2(yUnitVector, vecjoint3)
        self.joint4.data = self.angleBetweenVectors2(self.vectorYB, self.vectorBR)

        self.joint1.data = self.angleBound(self.joint1.data, np.pi)
        self.joint3.data = self.angleBound(self.joint3.data, np.pi / 2.0)
        self.joint4.data = self.angleBound(self.joint4.data, np.pi / 2.0)

    def pythagoras(self, a, b):
        return ((a ** 2) + (b ** 2)) ** 0.5

    def angleBound(self, jointAngle, limit):
        jointAngle = max(min(jointAngle, limit), -limit)
        return jointAngle

    def angleBetweenVectors(self, vectorFrom, vectorTo):
        return np.arctan2(np.cross(vectorTo, vectorFrom), np.dot(vectorFrom, vectorTo))

    def angleBetweenVectors2(self, vectorFrom, vectorTo):
        return np.arctan2(np.linalg.norm(np.cross(vectorTo, vectorFrom)), np.dot(vectorFrom, vectorTo))

    def combinecenters(self):
        self.originPoint = self.originhandler(self.greenC1, self.greenC2)
        self.finalRedCenter = self.centercamfusion(self.redC1, self.redC2)
        self.finalBlueCenter = self.centercamfusion(self.blueC1, self.blueC2)
        self.finalYellowCenter = self.centercamfusion(self.yellowC1, self.yellowC2)

    def centercamfusion(self, campoint1, campoint2):
        if (campoint1.size == 0) and (campoint2.size == 0):
            return np.array([-1.0, -1.0, -1.0])
        elif campoint1.size == 0:
            return np.array([self.originPoint[0], campoint2[0], campoint2[1]])
        elif campoint2.size == 0:
            return np.array([campoint1[0], self.originPoint[1], campoint1[1]])
        elif (campoint1.size == 2) and (campoint2.size == 2):
            return np.array([campoint1[0], campoint2[0], (campoint2[1] + campoint1[1]) / 2])
        else:
            return np.array([-1.0, -1.0, -1.0])


    def originhandler(self, campoint1, campoint2):
        if (campoint1.size == 0) and (campoint2.size == 0):
            return np.array([-1.0, -1.0, -1.0])
        elif campoint1.size == 0:
            return np.array([campoint2[0], campoint2[0], campoint2[1]])
        elif campoint2.size == 0:
            return np.array([campoint1[0], campoint1[0], campoint1[1]])
        elif (campoint1.size == 2) and (campoint2.size == 2):
            return np.array([campoint1[0], campoint2[0], (campoint2[1] + campoint1[1]) / 2])
        else:
            return np.array([-1.0, -1.0, -1.0])


# call the class
def main(args):
    v2 = vision_2()
    try:
        rospy.spin()
    except KeyboardInterrupt:
        print("Shutting down")
    cv2.destroyAllWindows()
    # run the code if the node is called


if __name__ == '__main__':
    main(sys.argv)
