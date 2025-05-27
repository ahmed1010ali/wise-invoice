from HelperFunctions.Libraries import *
def convert_image_to_pdf(image_content: bytes) -> bytes:
    try:
        img = Image.open(io.BytesIO(image_content))
        pdf_bytes = io.BytesIO()
        img.convert('RGB').save(pdf_bytes, format='PDF')
        pdf_data = pdf_bytes.getvalue()
        return pdf_data
    except Exception as e:
        print(f"Error converting image to PDF: {e}")
        return None
    
def deskew_image(image):
    # Convert to grayscale if image is in color
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image.copy()

    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Hough Line Transform to detect lines
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    if lines is None:
        print("No lines detected!")
        return image, 0

    # Collect angles of the lines
    angles = []
    for line in lines:
        rho, theta = line[0]
        angle = (theta * 180 / np.pi) - 90  # Convert to degrees
        angles.append(angle)

    # Compute the median angle
    skew_angle = np.median(angles)
    print("Detected skew angle:", skew_angle)

    # Rotate the image to deskew it
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    return rotated, skew_angle

def process_file_and_get_pdf(filename: str, file_content: bytes) -> bytes:
    if filename.endswith(".pdf"):
        # Convert PDF to image
        images = convert_from_bytes(file_content)
        np_images = np.array(images[0])
        # Deskew the image
        rotated_img, angle = deskew_image(np_images)
        rotated_img = cv2.cvtColor(rotated_img, cv2.COLOR_RGB2GRAY)
        # Convert the deskewed image back to PDF
        pdf_data = convert_image_to_pdf(cv2.imencode('.png', rotated_img)[1].tobytes())  # changed
    elif filename.endswith((".jpg", ".jpeg", ".png")):
        # Read image with cv2
        nparr = np.frombuffer(file_content, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # Deskew the image
        rotated_img, angle = deskew_image(image)
        rotated_img = cv2.cvtColor(rotated_img, cv2.COLOR_BGR2RGB)  # Added color conversion
        # Convert the deskewed image to PDF
        pdf_data = convert_image_to_pdf(cv2.imencode('.png', rotated_img)[1].tobytes())  # changed
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    return pdf_data
