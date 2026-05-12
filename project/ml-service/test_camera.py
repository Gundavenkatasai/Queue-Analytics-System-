"""
Simple camera test to diagnose issues
"""
import cv2
import sys

print("🎥 Testing Camera Connection...\n")

# Test 1: Default backend
print("1️⃣ Testing with default backend...")
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()

if ret:
    print("✅ Camera works with default backend!")
    sys.exit(0)
else:
    print("❌ Camera failed with default backend")

# Test 2: DirectShow backend
print("\n2️⃣ Testing with DirectShow backend...")
try:
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        print("✅ Camera works with DirectShow!")
        sys.exit(0)
    else:
        print("❌ Camera failed with DirectShow")
except Exception as e:
    print(f"❌ DirectShow error: {e}")

# Test 3: List available cameras
print("\n3️⃣ Checking available camera devices...")
for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"✅ Camera found at index {i}")
            cap.release()
            sys.exit(0)
        cap.release()

print("\n❌ NO WORKING CAMERAS FOUND!")
print("\n💡 Troubleshooting:")
print("   • Check Device Manager for camera devices")
print("   • Verify camera drivers are installed")
print("   • Try connecting the camera to a different USB port")
print("   • Restart your computer")
print("   • Check Windows Settings > Privacy > Camera permissions")
