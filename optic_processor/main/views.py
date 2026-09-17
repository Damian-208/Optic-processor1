from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import SignUpForm
from django.http import HttpResponse, Http404
from django.conf import settings
import os
from .image_processing import process_uploaded_image, vertical_options, horizontal_options, special_options
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import Answer
# Create your views here.

def home(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            messages.success(request, 'You are now logged in')
            return redirect('home')
        else:
            messages.success(request, 'Error logging in')
            return redirect('home')
    else:

        return render(request, 'home.html', {})

def process_image(request):
    if request.method == 'POST':
        selected_item1 = request.POST.get('selectedBook')
        selected_item2 = request.POST.get('selectedOptic')
        results = []
        images = request.FILES.getlist('images[]')
        if images:
            for image in images:

                temp_image_path = os.path.join(settings.MEDIA_ROOT, 'temp.jpeg')
                with open(temp_image_path, 'wb+') as destination:
                    for chunk in image.chunks():
                        destination.write(chunk)
                

                results.append(process_uploaded_image('temp.jpeg', selected_item2))
        
        request.session['results'] = results
        request.session['selected_book'] = selected_item1

        return HttpResponseRedirect(reverse('image_process_results'))
    

    return redirect('home')

def compare_answers(answer_sheet, options):
    nums_correct = 0
    nums_wrong = 0
    nums_empty = 0
    tracked_answers = []

    for i in range(len(answer_sheet)):
        if options[i][1] == answer_sheet[i]:
            nums_correct += 1
            tracked_answers.append([i+1, 'Correct'])
        elif options[i][1] == 'EMPTY':
            nums_empty += 1
            tracked_answers.append([i+1, 'Empty'])
        else:
            nums_wrong += 1
            tracked_answers.append([i+1, 'Wrong'])
    
    formatted_tracked_answers = ''

    for answer in tracked_answers:
        formatted_tracked_answers += str(answer[0]) + '-' + answer[1] + '  ' + '\n'

    return {'correct': str(nums_correct), 'wrong': str(nums_wrong), 'empty': str(nums_empty), 'tracked_answers': formatted_tracked_answers}


def combine_answers(options):
    options = [x[1] for x in options]
    combined_str = ''.join(options)
    return combined_str

def image_process_results(request):
    results = request.session.get('results', []) # results is a list of dictionaries
    # each dictionary contains the name of the field and a list of lists of options that was selected on the optic pertaining to that field
    selected_book = request.session.get('selected_book', None) # this is the name of the book that was selected

    # here comparing with the answer sheet. getting num of correct or wrong or empty answers
    formatted_results = []
    for result in results:
        answers = None
        if 'book_type' in result and 'exam_type' in result:
            answers = Answer.objects.get(name = selected_book, book_type = result['book_type'], exam_type = result['exam_type'])

        dict_to_add = {}

        if 'student_number' in result:
            formatted_name = 'Student Number'
            combined_str = combine_answers(result['student_number'])
            dict_to_add[formatted_name] = {'SingleKey': combined_str}
        
        if 'book_type' in result:
            formatted_name = 'Book Type'
            dict_to_add[formatted_name] = {'SingleKey': result['book_type']}
        
        if 'exam_type' in result:
            formatted_name = 'Exam Type'
            dict_to_add[formatted_name] = {'SingleKey': result['exam_type']}
        
        if 'turkish' in result:
            formatted_name = 'Turkish Questions'
            compared_answers = compare_answers(answers.turkish, result['turkish'])
            dict_to_add[formatted_name] = {'Correct': compared_answers['correct'], 'Wrong': compared_answers['wrong'], 'Empty': compared_answers['empty'], 'Tracked Answers': compared_answers['tracked_answers']}        
        
        if 'maths' in result:
            formatted_name = 'Maths'
            compared_answers = compare_answers(answers.maths, result['maths'])
            dict_to_add[formatted_name] = {'Correct': compared_answers['correct'], 'Wrong': compared_answers['wrong'], 'Empty': compared_answers['empty'], 'Tracked Answers': compared_answers['tracked_answers']}

        if 'social_sciences' in result:
            formatted_name = 'Social Sciences'
            compared_answers = compare_answers(answers.social_sciences, result['social_sciences'])
            dict_to_add[formatted_name] = {'Correct': compared_answers['correct'], 'Wrong': compared_answers['wrong'], 'Empty': compared_answers['empty'], 'Tracked Answers': compared_answers['tracked_answers']}

        if 'fen_sciences' in result:
            formatted_name = 'Fen'
            compared_answers = compare_answers(answers.fen_sciences, result['fen_sciences'])
            dict_to_add[formatted_name] = {'Correct': compared_answers['correct'], 'Wrong': compared_answers['wrong'], 'Empty': compared_answers['empty'], 'Tracked Answers': compared_answers['tracked_answers']}
        

        formatted_results.append(dict_to_add)
        dict_to_add = {}

    return render(request, 'image_process_results.html', {'data': formatted_results})   
    
        # for name, options in result.items():
        #     if name == 'turkish':
        #         turkish_answers = answers.turkish # turkish_answers is a big string like AAAABBBBCCCCDDDEEE
        #         compared_answers = compare_answers(turkish_answers, options)
        #         formatted_name = 'Turkish Questions'
        #     elif name == 'maths':
        #         maths_answers = answers.maths
        #         compared_answers = compare_answers(maths_answers, options)
        #         formatted_name = 'Maths'
        #     elif name == 'social_sciences':
        #         social_sciences_answers = answers.social_sciences
        #         compared_answers = compare_answers(social_sciences_answers, options)
        #         formatted_name = 'Social Sciences'
        #     elif name == 'fen_sciences':
        #         fen_sciences_answers = answers.fen_sciences
        #         compared_answers = compare_answers(fen_sciences_answers, options)
        #         formatted_name = 'Fen Sciences'
        #     elif name == 'book_type':
        #         formatted_name = 'Book Type'
        #         dict_to_add[formatted_name] = {formatted_name: options}
        #         continue
        #     elif name == 'exam_type':
        #         formatted_name = 'Exam Type'
        #         dict_to_add[formatted_name] = {formatted_name: options}
        #         continue
        #     elif name == 'student_number':
        #         formatted_name = 'Student Number'
        #         combined_str = combine_answers(options)
        #         dict_to_add[formatted_name] = {formatted_name: combined_str}
        #         continue

        #     dict_to_add[formatted_name] = {'Number of Correct Answers': compared_answers['correct'], 
        #                                          'Number of Wrong Answers': compared_answers['wrong'],
        #                                          'Number of Empty Answers': compared_answers['empty'],
        #                                          'Details': compared_answers['tracked_answers']}

def logout_user(request):
    logout(request)
    messages.success(request, 'You are now logged out')
    return redirect('home')

def register_user(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)

        if form.is_valid():
            form.save()

            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']

            user = authenticate(username=username, password=password)

            login(request, user)

            messages.success(request, 'You have successfully registered and logged in')
            return redirect('home')
    else:
        form = SignUpForm()
        return render(request, 'register.html', {'form': form})

    return render(request, 'register.html', {'form': form})

def serve_image(request):
    item = request.GET.get('item', None)
    
    if item is None:
        raise Http404("Item not specified")

    # Define the path to the directory containing your images
    image_directory = os.path.join(settings.BASE_DIR, 'media/sample_images')
    
    # Define the path to the image
    image_path = os.path.join(image_directory, f"{item}.jpg")

    if not os.path.exists(image_path):
        raise Http404("Image not found")

    with open(image_path, 'rb') as img_file:
        response = HttpResponse(img_file.read(), content_type='image/png')
        response['Content-Disposition'] = f'inline; filename="{item}.png"'
        return response
