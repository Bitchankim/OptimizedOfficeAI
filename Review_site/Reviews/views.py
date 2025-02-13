from django.shortcuts import render, redirect, get_object_or_404, HttpResponse, reverse
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from Reviews.models import Review_Models
from .forms import FileUploadForm, RegistrationForm, LoginForm, DeleteAccountForm

# 로그인 및 회원가입에 관한 모듈들 
from .models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout


import tensorflow as tf
from tensorflow.keras.preprocessing import image

from ultralytics import YOLO

import time
import math

# views.py : 웹 페이지의 동작 로직을 정의하는 파일

# 사용자가 업로드한 파일이 저장되는 경로 (로컬 폴더)

FILE_PATH = "/Users/bchank/Team_project_2/OptimizedOfficeAI/Review_site"

# Create your views here.
def home(request):
    return render(request,'Reviews/home.html')

def about(request):
    return render(request,'Reviews/about.html')

def manual(request):
    return render(request,'Reviews/usermanual.html')

def aboutus(request):
    return render(request,'Reviews/aboutus.html')

def calculate_distance(point):
    x_centroid , y_centroid = 0.5, 0.5
    return math.sqrt((x_centroid - point[0])**2 + (y_centroid - point[1])**2)

# 이미지 도메인 분류 로직
def img_domain_clf(img_url):

    # 이미지 경로 설정
    path = FILE_PATH + img_url

    # 이미지 로드
    img = image.load_img(path, target_size=(224, 224))

    # 이미지 전처리
    img = image.img_to_array(img)
    img = img / 255.0
    img = tf.expand_dims(img, axis=0)

    # AI 모델 로드 (파일 형식 : h5)
    model = tf.keras.models.load_model(FILE_PATH + '/ai_models/CNN_Model_Dataset2.h5', compile=False)
    
    # 이미지 분류 수행

    # 추론 시간 측정을 위한 코드는 현 주석 처리 (start_time ~ diff_time)
    # start_time = time.time()
    prediction = model.predict(img)
    # end_time = time.time()

    # diff_time = end_time - start_time
    
    # 0.5를 기준으로 0.5를 초과하는 경우 '사내 제품 홍보용 사진'으로 분류
    # 0.5 미만인 경우 '실제 사용 사진(리뷰)'으로 분류
    result = prediction[0][0]
    if result > 0.5:
        domain = '제품'
    else:
        domain = '실사용'
    
    # 결과값 리턴
    return domain

# 이미지 클래스 분류 로직
def img_object_clf(img_url):
    # 이미지 경로 설정
    path = FILE_PATH + img_url

    # 모델 불러오기 
    model = YOLO(FILE_PATH + "/ai_models/best.pt")
    names = model.names

    # 이미지 분류 수행
    # start_time = time.time()
    result = model.predict(source=path)
    # end_time = time.time()

    # diff_time = end_time - start_time

    #오브젝트별 중심 거리 
    distances = []
    objects_list = []

    # result 내의 결과값들
    for r in result:
        for box in r.boxes:
            x1 = float(box.xyxyn[0][0])
            y1 = float(box.xyxyn[0][1])
            x2 = float(box.xyxyn[0][2])
            y2 = float(box.xyxyn[0][3])

            x_mid , y_mid = ( x1 + x2 ) / 2 , ( y1 + y2 ) / 2
            mid = [x_mid, y_mid]
            distance = calculate_distance(mid)
            distances.append(distance)

            # class id 에 해당하는 이름 리스트에 추가(리스트 안에 없는 경우에만)
            if names[int(box.cls)] not in objects_list:
                objects_list.append(names[int(box.cls)])

    # try:
    #     object_clf = objects_list[distances.index(min(distances))]
    # except:
    #     object_clf = "None"

    return objects_list

# Class 매핑 딕셔너리
PRODUCT_MAPPING = {
    "back_pack": "Back Pack",
    "bike": "Bike",
    "bike_helmet": "Bike Helmet",
    "bookcase": "Book Case",
    "bottle": "Bottle",
    "calculator": "Calculator",
    "desk_chair": "Desk Chair",
    "desk_lamp": "Desk Lamp",
    "desktop_computer": "Desktop",
    "file_cabinet": "File Cabinet",
    "headphones": "Headphone",
    "keyboard": "Keyboard",
    "laptop_computer": "Laptop",
    "letter_tray": "Letter Tray",
    "mobile_phone": "Mobile Phone",
    "monitor": "monitor",
    "mouse": "Mouse",
    "mug": "Mug",
    "paper_notebook": "Paper Notebook",
    "phone": "Phone",
    "printer": "Printer",
    "projector": "Projector",
    "punchers": "Puncher",
    "ring_binder": "Ring Binder",
    "ruler": "Ruler",
    "scissors": "Scissor",
    "speaker": "Speaker",
    "stapler": "Stapler",
    "tape_dispenser": "Tape Dispenser",
    "trash_can": "Trash Can"
}

# Value 에서 딕셔너리 key 찾기
def get_key_by_value(dict, value):
    for key, val in dict.items():
        if val == value:
            return key
    return None

# 리뷰 조회 페이지 로직
def index(request):
    # stars = {
    #     '⭐️⭐️⭐️⭐️⭐️':5,
    #     '⭐️⭐️⭐️⭐️':4,
    #     '⭐️⭐️⭐️':3,
    #     '⭐️⭐️':2,
    #     '⭐️':1
    # }
    #### 정렬 기능 
    # sort GET (값이 없다면 '최신 순')
    # domain GET (값이 없다면 'ALL')
    # product GET (값이 없다면 'ALL')
    # star GET (값이 없다면 'ALL')
    sort = request.GET.get('sort', '최신 순')
    domain = request.GET.get('domain', 'ALL')
    product = request.GET.get('product', 'ALL')
    star = request.GET.get('star', 'ALL')
    
    # ORM
    # 날짜와 관련한 정렬
    if sort == '최신등록순':
        reviews = Review_Models.objects.all().order_by('-dt_created')
    # 별점과 관련한 정렬
    elif sort == '별점높은순':
        reviews = Review_Models.objects.all().order_by('-ratings', '-dt_created')
    elif sort == '별점낮은순':
        reviews = Review_Models.objects.all().order_by('ratings', '-dt_created')
    # 정렬 없을 떄
    else:
        reviews = Review_Models.objects.all().order_by('-dt_created') # 데이터 전체 불러오기

    # 도메인 필터
    if domain is not None and domain != 'ALL':
        reviews = reviews.filter(domain_clf=domain)
    # 제품 필터
    if product is not None and product != 'ALL':
        mapped_product = get_key_by_value(PRODUCT_MAPPING, product)  
        reviews = reviews.filter(objects_clf__contains=mapped_product)
    # 별점 필터
    if star is not None and star != 'ALL':
        reviews = reviews.filter(ratings=star)
        star = '⭐' * int(star)
    
    # paginator 객체 생성(queryset, 한 페이지에서 보여줄 포스트 개수)
    paginator = Paginator(reviews, 9)
    page = request.GET.get('page', 1) # page라는 명으로 들러온 값을 가져오겠다(ex) ~/?page=4
    page_obj = paginator.get_page(page) # 페이지가 숫자가 아닌 경우 첫 페이지를 반환, 음수나 범위를 벗어난 경우 마지막 페이지 반환 -> Page 객체 반환

    return render(request, 'Reviews/index.html', {'page_obj':page_obj,'page':page, 'paginator':paginator, 'sort':sort, 'domain':domain, 'product':product, 'star':star, 'PRODUCT_MAPPING':PRODUCT_MAPPING})

# 리뷰 업로드 페이지 로직
@csrf_exempt
def upload(request):
    ### 사용자가 폼을 통해 입력을 했을 경우, 
    if request.method == 'POST':

        # 입력된 내용들을 form이라는 변수에 저장
        form = FileUploadForm(request.POST, request.FILES)
        # 유효성 검사
        if form.is_valid(): 
            
            # form 데이터 저장(임시 저장)
            post = form.save(commit=False) 
            post.user = request.user
            # form 데이터를 DB에 저장
            post.save()                    

            ### 데이터 분류 로직 ###
            review = Review_Models.objects.get(id=post.id)

            # 이미지 분류 함수 호출(이미지는 url형태로 넘겨주기)
            cnn_result = img_domain_clf(review.imgfile.url)
            yolo_result = img_object_clf(review.imgfile.url)

             # 결과를 받아와서 필드 값 수정 및 저장
            review.domain_clf = cnn_result
            review.objects_clf = yolo_result
            review.save()

            # 결과보기 페이지에 id 값 같이 넘겨주기
            return redirect('detail', post_id=post.id)
        
    ### 사용자가 입력하기 전, 새로운 폼을 생성
    else:
        form = FileUploadForm()

    # form이 유효하지 않다면, 기존 form 형식 유지 
    return render(request, 'Reviews/review_upload.html', {'form':form})

# 리뷰 상세보기 페이지 로직
def detail(request, post_id):
    review = Review_Models.objects.get(id=post_id)

    return render(request, 'Reviews/review_detail.html', {'review':review})

# 리뷰 수정페이지 로직
@csrf_exempt
def update(request, post_id):
    review = Review_Models.objects.get(id=post_id)

    ### 사용자가 폼을 통해 입력을 했을 경우, 
    if request.method == 'POST':
        # 입력된 내용들을 form이라는 변수에 저장
        update_form = FileUploadForm(request.POST, request.FILES, instance=review)

        if update_form.is_valid():
            # form 데이터 저장(임시 저장) 
            post = update_form.save(commit=False) 
            # form 데이터를 DB에 저장
            post.save() 

            ### 데이터 분류 로직 ###
            review = Review_Models.objects.get(id=post.id)

            # 이미지 분류 함수 호출(이미지는 url형태로 넘겨주기)
            cnn_result = img_domain_clf(review.imgfile.url)
            yolo_result = img_object_clf(review.imgfile.url)

             # 결과를 받아와서 필드 값 수정 및 저장
            review.domain_clf = cnn_result
            review.objects_clf = yolo_result
            review.save()

            # 결과보기 페이지에 id 값 같이 넘겨주기
            return redirect('detail', post_id=post.id)
    else:
        # 기존에 입력받은 데이터를 그대로 출력
        update_form = FileUploadForm(instance=review)

    return render(request, 'Reviews/review_upload.html', {'form':update_form, 'review':review})

# 리뷰 삭제 페이지
@csrf_exempt
def delete(request, post_id):
    review = Review_Models.objects.get(id=post_id)
    review.delete()

    return redirect('index')

# 로그인 관련 함수 정의
@csrf_exempt
def login_view(request):

    # Base_with_nav_html에 있는 상단 로그인 버튼을 클릭하는 경우, 즉 요청이 Post가 아닌 경우 
    # Login 관련 html로 렌더링
    if request.method =='GET':
        form = LoginForm()
        return render(request, 'Reviews/login.html', {'form': form})
    
    elif request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # 이메일과 비밀번호를 사용하여 인증을 수행
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # 인증에 성공한 경우, 로그인 처리
                login(request, user)
                return redirect('index')  # 로그인 후 이동할 페이지로 변경
            else:
                message = '유효하지 않은 이메일 또는 비밀번호입니다.'
                return render(request, 'Reviews/login.html', {'form': form, 'message': message})
        else:
            return render(request, 'Reviews/login.html', {'form': form})

# 회원 가입에 관한 함수 정의
@csrf_exempt
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            confirm_password = form.cleaned_data['confirm_password']

            if password != confirm_password:
                message = '비밀번호가 일치하지 않습니다.'
                return render(request, 'Reviews/register.html', {'form': form, 'message': message})

            if password == confirm_password:
                try:
                    User.objects.get(username=username)
                    message = '이미 사용 중인 아이디입니다.'
                    return render(request, 'Reviews/register.html', {'form': form, 'message': message})
                except User.DoesNotExist:
                    user = User(
                       # email=email,
                        username=username,
                        password=make_password(password)
                    )
                    user.save()
                    message = '회원가입이 완료되었습니다.'
                    return render(request, 'Reviews/register.html', {'form': form, 'message': message})
        
    elif request.method == 'GET':
        form = RegistrationForm()
    
    return render(request, 'Reviews/register.html', {'form': form})

# 회원 탈퇴에 관한 함수 정의
@csrf_exempt
@login_required
def deleteaccount(request):
    # form = DeleteAccountForm()

    if request.method == 'POST':
        user = request.user
        password = request.POST['password']

        # 비밀번호 확인 절차
        if user.check_password(password):
            # 사용자 계정을 삭제한 후 로그아웃 처리
            user.delete()
            logout(request)
            message = '회원 탈퇴가 완료되었습니다.'
            return render(request, 'Reviews/delete_account.html', {'message':message})
        
        else:   
            message = '비밀 번호가 올바르지 않습니다.'
            return render(request, 'Reviews/delete_account.html', {'message':message})
                  
    if request.method == 'GET':
        return render(request, 'Reviews/delete_account.html')

@csrf_exempt
def logout_view(request):
    logout(request)  # 로그아웃 실행
    return redirect('index') 
