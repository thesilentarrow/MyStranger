from django.shortcuts import render, redirect
from django.http import HttpResponse
from qna.models import PublicChatRoom, Answer, Polls
import json
from django.db.models import Count
from django.contrib import messages
from account.models import Account

from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from django.db.models import Count
from django.template.loader import render_to_string
from django.template import RequestContext


import io
from PIL import Image, ImageOps
from io import BytesIO
from django.core.files.base import ContentFile

from moviepy.editor import VideoFileClip
from moviepy.video import fx  # Import the fx module
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files import File
from io import BytesIO

import os
import tempfile
import json
import subprocess






# Create your views here.
def pika_view(request):

    # if not request.user.is_authenticated:
    #     return redirect('login')

    if request.user.is_authenticated:
        user = request.user
        user.update_last_activity()

    context = {}


    # question_answers = [] # ['{question' : {answers}}]

    # questions = PublicChatRoom.objects.all()
    questions = PublicChatRoom.objects.all().order_by('-timestamp')
    # questions = PublicChatRoom.objects.all().exclude(answers__user = request.user)
    questions = questions.order_by('-timestamp')

    unpolled_questions = []
    for question in questions:
       
        print('question - ', question)

        '''
        check if the question is already polled than don't show it to the user
        '''
        # skip_outer_loop = False
        # for poll in question.polls.all():
        #     if request.user in poll.polled.all():
        #         # print('The user has already polled this quest &&&&&&&&&&&&&&&')
        #         skip_outer_loop = True
        #         break  # exit the inner loop

        # if skip_outer_loop:
        #     continue  # skip the remaining iterations of the outer loop

        unpolled_questions.append(question)
    
    # Number of questions to display per page
    questions_per_page = 5

    paginator = Paginator(unpolled_questions, questions_per_page)
    page = request.GET.get('page', 1)

    try:
        questions_page = paginator.page(page)
    except PageNotAnInteger:
        # If the page is not an integer, deliver the first page.
        questions_page = paginator.page(1)
    except EmptyPage:
        # If the page is out of range (e.g. 9999), deliver the last page of results.
        questions_page = paginator.page(paginator.num_pages)

    # Access the questions for the current page
    current_page_questions = questions_page.object_list

    context['the_questions'] = questions_page
    print('this is the questions page - ',current_page_questions)
    my_list = qna_payload(request, current_page_questions)

    print(my_list)


    # # Your existing code to retrieve questions
    # questions = PublicChatRoom.objects.all().order_by('-timestamp')
    # questions_per_page = 5

    # paginator = Paginator(questions, questions_per_page)
    # page = request.GET.get('page', 1)

    try:
        questions_page = paginator.page(page)
    except PageNotAnInteger:
        questions_page = paginator.page(1)
    except EmptyPage:
        questions_page = paginator.page(paginator.num_pages)

    current_page_questions = questions_page.object_list

    context = {
        'the_questions': questions_page,
    }

    print('this is the questions page - ',current_page_questions)
    my_list = qna_payload(request, current_page_questions)

    # print(my_list)
    context['question_top2_answers'] = my_list

    if request.GET.get('action') == 'new_ques':
        # If it's an AJAX request, return JSON response
        print('the ajax request is getting processed')
       
        data = {
            'html': render_to_string('qna/question_partial.html', {'question_top2_answers': my_list,'the_questions': questions_page}, request=request),
            'has_next': questions_page.has_next(),
        }
        # print('the fuckin data - ', data)
        return JsonResponse(data)

    # for question in questions:
    #     # question_answers.append([question, question.answers.all()])
    #     # print('question - ', question)

    #     '''
    #     check if the question is already polled than don't show it to the user
    #     '''
    #     skip_outer_loop = False
    #     for poll in question.polls.all():
    #         if request.user in poll.polled.all():
    #             # print('The user has already polled this quest &&&&&&&&&&&&&&&')
    #             skip_outer_loop = True
    #             break  # exit the inner loop

    #     if skip_outer_loop:
    #         continue  # skip the remaining iterations of the outer loop

    #     answers_with_descendants = []

    #     answers = question.answers.filter(parent=None).annotate(report_count=Count('ans_reports')).exclude(report_count__gt=10)
    #     answers = answers.annotate(num_likes=Count('likes'))
    #     answers = answers.order_by('-num_likes')[:1]

    #     top2_ans = []
    #     for answer in answers:
    #         # print('The parent answer - ', answer)
            
    #         answers_and_replies = [answer] + list(answer.get_descendants())
    #         answers_with_descendants.extend(answers_and_replies) 
    #         top2_ans.append(answer.pk)
        
    #     # assuming that above instead of sending the first 2 answers we have send the top 2 answers , now we want to send the rest of the answers excluding the above 2

    #     other_answers_with_descendants = []

    #     if not question.polls.all():
    #         answers = question.answers.filter(parent=None).exclude(id__in=top2_ans)
    #     else:
    #         answers = question.answers.filter(parent=None)
    #     answers = answers.order_by('-timestamp')
    #     for answer in answers:
    #         # print('This is what the pending answers are - ', answer)
    #         print('The answer - ',answer,' The reports - ',answer.ans_reports.all().count())
    #         if answer.ans_reports.all().count() < 5:
    #             other_answers_and_replies = [answer] + list(answer.get_descendants())
    #             other_answers_with_descendants.extend(other_answers_and_replies) 
        


        
    #     question_answers.append([question,answers_with_descendants, other_answers_with_descendants])
            
        
   
    # context['question_top2_answers'] = my_list
    context['is_active'] = 'qna'
    # print('this is my fuckin context - ', context)

    return render(request, "qna/questions.html", context)

def create_post_view(request):

    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':

        user = request.user
        question = request.POST.get('question')

        poll1 = request.POST.get('poll1')
        poll2 = request.POST.get('poll2')
        poll3 = request.POST.get('poll3')
        poll4 = request.POST.get('poll4')

        
        if poll1 or poll2 or poll3 or poll4:
            #This means this questions has polls in it

            polls_list = [poll1,poll2,poll3,poll4]
            counter = 0
            for poll in polls_list:
                if poll:
                    counter += 1
            if counter <2:
                messages.warning(request, 'Please add atleast two poles or add none...')
                return redirect('qna:create-post')
            roomv = PublicChatRoom(question = question, owner = user)
            roomv.save()
            for poll in polls_list:
                if poll:
                    pollva = Polls(question = roomv, option=poll)
                    pollva.save()
        else:
            roomv = PublicChatRoom(question = question, owner = user)
            roomv.save()
            
        # Check if an image was uploaded
        if 'image' in request.FILES:
            # image = request.FILES['image']

            file = request.FILES['image']
            # Check the file type
            if file.content_type.startswith('image/'):
                # It's an image
                # Save it to the image field
                # model_instance = PublicChatRoom(image=file, ...)
                 # Check if the image size is less than 10 MB
                image = file
                if image.size > 10 * 1024 * 1024:
                    return HttpResponse("File should be less than 10 MB", status=400)

                # Compress the image before saving
                compressed_image = compress_image(image)

                roomv.image = compressed_image
                roomv.save()
            elif file.content_type.startswith('video/'):
                # It's a video
                # Check if the video size is greater than 50MB
                video_file = file
                max_size_mb = 100
                max_size_bytes = max_size_mb * 1024 * 1024

                # # Save the TemporaryFile to disk
                # temp_dir = tempfile.gettempdir()
                # temp_file_path = os.path.join(temp_dir, video_file.name)
                # with open(temp_file_path, 'wb+') as out:
                #     out.write(video_file.file.read())

                # # Load the video clip from the file path
                # video_clip = VideoFileClip(temp_file_path)

                # # # check the length of the video in seconds

                # duration = video_clip.duration
                # print('The video is this long - ', duration)
                # if int(duration) > 300:
                #     return HttpResponse("The video can not be longer than 5 Minutes.", status=400)

                # # Delete the temporary file
                # os.remove(temp_file_path)


                if file.size > max_size_bytes:
                    # the file is big so return the msg
                    return HttpResponse("File should be less than 100 MB", status=400)
                elif file.size > 50*1024*1024 and file.size < 100*1024*1024:
                    # Video size is greater than 50MB, compress it
                    compressed_video = compress_video(file)
                    roomv.video = compressed_video
                    roomv.save()

                    # # Generate the thumbnail
                    # thumbnail_path = generate_thumbnail(roomv.video.path)

                    # # Save the thumbnail to your Django model
                    # roomv.thumbnail = thumbnail_path
                    # roomv.save()
                else:
                    # # Video size is greater than 50MB, compress it
                    # compressed_video = compress_video(file)
                    # roomv.video = compressed_video
                    roomv.video = file
                    roomv.save()
                    
                    # print('generating thumbnail')
                    # # Generate the thumbnail
                    # thumbnail_path = generate_thumbnail(file)

                    # # Save the thumbnail to your Django model
                    # roomv.thumbnail = thumbnail_path
                    # roomv.save()

            else:
                # Invalid file type
                # Handle the error
                print('what the fuck is in the input')
                pass


        return redirect('qna:pika')

    return render(request, "qna/create_question.html")

def minichat_view(request, *args, **kwargs):
    return render(request, "qna/qnaroom.html")


def addAnswer_view(request, *args, **kwargs):

    print('The addAnswer view is called')
    user = request.user

    if not request.user.is_authenticated:
        return redirect("login")

    if request.POST:

        if request.POST.get('action') == 'report':

            print('ans report request arrived')
            id = request.POST.get('node-id')
            reporter = request.user

            try:
                answer = Answer.objects.get(pk=id)
                if reporter in answer.ans_reports.all():
                    # You have already reported this person
                    response_data = {
                'status' : 'success',
                'response' : 'Already Reported',
            }
                else:
                    # The person is reported 
                    answer.add_flag(reporter)
                    response_data = {
                'status' : 'success',
                'response' : 'reported',
            }
                
                print('This answer/reply is getting reported - ', answer)

            except Exception as e :
                print('error fetching the answer')
                response_data = {
                'status' : 'error',
                'message': str(e),
            }


        if request.POST.get('action') == 'delete':

            print('post delete request arrived')

            id = request.POST.get('node-id')
            print('The delete id is -', id)
            try:
                answer = Answer.objects.get(pk=id)
                print('This answer is getting deleted - ', answer)

                if answer.user == request.user:
                    answer.delete()

                response_data = {
                'status' : 'delete done',
                'response' : 'card deleted'
            }
            except Exception as e:
                print('error fetching the answer')
                response_data = {
                'status' : 'error',
                'message': str(e),
            }


           
            return HttpResponse(json.dumps(response_data), content_type="application/json")
        
        if request.POST.get('action') == 'delete_my_question':

            print('post delete question request arrived')

            id = request.POST.get('node-id')
            print('The delete question id is -', id)
            try:
                question = PublicChatRoom.objects.get(pk=id)
                print('This question is getting deleted - ', question)

                if question.owner == request.user:
                    question.delete()

                response_data = {
                'status' : 'delete done',
                'response' : 'card deleted'
            }
            except Exception as e:
                print('error fetching the answer')
                response_data = {
                'status' : 'error',
                'message': str(e),
            }


           
            return HttpResponse(json.dumps(response_data), content_type="application/json")
        

        if request.POST.get('action') == 'like':

            print('post like request arrived')
            id = request.POST.get('node-id')

            try:
                answer = Answer.objects.get(pk=id)
                answer.add_like(request.user)
                count = answer.likes.all().count()
                response_data = {
                'status' : 'like added',
                'response' : 'liked',
                'count' : count,
            }
            except Exception as e:
                print('error fetching the answer')
                response_data = {
                'status' : 'error',
                'message': str(e),
            }
            
            return HttpResponse(json.dumps(response_data), content_type="application/json")
        
        if request.POST.get('action') == 'unlike':

            print('post unlike request arrived')
            id = request.POST.get('node-id')

            try:
                answer = Answer.objects.get(pk=id)
                answer.remove_like(request.user)
                
                response_data = {
                'status' : 'unlike added',
                'response' : 'unliked',
                
            }
            except Exception as e:
                print('error fetching the answer')
                response_data = {
                'status' : 'error',
                'message': str(e),
            }
            
            return HttpResponse(json.dumps(response_data), content_type="application/json")
        

        if request.POST.get('action') == 'poll-selected':

            print('poll selected request arrived')
            id = request.POST.get('poll-id')

            try:
            #     answer = Answer.objects.get(pk=id)
            #     answer.remove_like(request.user)
                poll = Polls.objects.get(id=id)
                poll.add_user(request.user)

                # now we wanna get a json with poll id and its percentage

                # for that first gonna fetch the question

                question = poll.question
                # print(question)

                empy_dict = {}
                total_polled = 0
                for poll in question.polls.all():
                    total_polled += poll.polled.all().count()
                
                for poll in question.polls.all():
                    empy_dict[poll.id] = round((poll.polled.all().count() / total_polled) * 100, 1)
                
                print('This is the empy dict with all the data regarding this ques and its polls - ', empy_dict)


                ac_poll_id = None
                try:
                    if request.POST.get('account') == 'yup':
                        account_id = request.POST.get('account_id')
                        account = Account.objects.get(id=account_id)
                        for poll in question.polls.all():
                            if account in poll.polled.all():
                                ac_poll_id = poll.id
                                break
                except Exception as e:
                    print('Error fetching what other user polled - ',str(e))


                response_data = {
                'status' : 'got_data',
                'response' : empy_dict,
                'total_polls' : total_polled,
                'ac_poll_id' : ac_poll_id,
                
            }
                
            except Exception as e:
                print('error fetching the data - ' , str(e))
                response_data = {
                'status' : 'error',
                'message': str(e),
            }
            
            
            return HttpResponse(json.dumps(response_data), content_type="application/json")


        try:
            
            question_id = request.POST.get('question-id')
            print('The question id is -', question_id)
            content = request.POST.get('id_chat_message_input')
            user = request.user

            try:
                question = PublicChatRoom.objects.get(pk=question_id)

                parent_id = request.POST.get('answer-id')
                print('The parent id is - ', parent_id)
                if parent_id:
                    if content:
                        parent = Answer.objects.get(pk=parent_id)
                        answer = Answer(question = question, user = user, content=content, parent=parent)
                        answer.save()
                        response_data = {
                            'status' : 'Replied',
                            'message': 'Your reply has been added.',
                            'name' : user.name,
                            'content' : content,
                            'domain' : user.university_name,
                            'nodeId' : answer.id,
                            
                        }
                    else:
                        response_data = {
                            'status' : 'empty_msg',

                        }
                else:
                    print('this is the before ans - ')
                    if content:
                        answer = Answer(question = question, user = user, content=content)
                        answer.save()
                        print('this is the ans - ', answer)
                        response_data = {
                            'status' : 'Answered',
                            'message': 'Your answer has been added.',
                            'name' : user.name,
                            'content' : content,
                            'domain' : user.university_name,
                            'nodeId' : answer.id,
                            
                        }
                    else:
                        response_data = {
                            'status' : 'empty_msg',

                        }

            except PublicChatRoom.DoesNotExist:
                print('Error - question/answer doesn not exist!')

        except Exception as e:
            print('The addAnswer/reply exception is - ', str(e))
            response_data = {
                'status' : 'error',
                'message': str(e),
            }

    return HttpResponse(json.dumps(response_data), content_type="application/json")


def show_ques_view(request,*args, **kwargs):

    ans_id = kwargs.get('ans_id')
    context = {}

    if request.user.is_authenticated:
        user = request.user
        user.update_last_activity()

    try:
        
        is_ques = request.GET.get('question')
        if not is_ques:
            answer = Answer.objects.get(pk=ans_id)
        else:
        # now check if its a question
            try:
                question = PublicChatRoom.objects.get(pk=ans_id)
                answer = question.answers.filter(parent=None).annotate(report_count=Count('ans_reports')).exclude(report_count__gt=10)
                answer = answer.annotate(num_likes=Count('likes'))
                answer = answer.order_by('-num_likes')[:1].first()
            except:
                return HttpResponse('The question/answer you are looking for does not exist! or is deleted!')
            
        ques_id = answer.question.id
        question = PublicChatRoom.objects.get(pk=ques_id)

        # now gotta check whether this answer is a answer or a reply
        if answer.parent:
            context['ans_id'] = int(ans_id)
            context['highlight_reply'] = int(ans_id)

            try:
                child_node = Answer.objects.get(id=ans_id)
                ancestors = child_node.get_ancestors(ascending=True)  # ascending=True returns ancestors from root to parent

                # ------------------------------------------------------------------------

                # nodes_to_expand = child_node.get_ancestors(include_self=True).values_list('id', flat=True)

                # # Pass nodes_to_expand to your template
                # context = {'nodes_to_expand': nodes_to_expand}

                # The first element in the ancestors list will be the root ancestor
                root_ancestor = child_node.get_root()
                parent_id = child_node.parent.id
                print('This is the fuckin parent id - ', parent_id)
                context['parent_id'] = parent_id

                answer = root_ancestor

                print('This is his parent root answer - ', root_ancestor)

                question_answers = [] # ['{question' : {answers}}]

                answers_with_descendants = []

                # answers = question.answers.filter(parent=None)
                # answers = answers.annotate(num_likes=Count('likes'))
                # answers = answers.order_by('-num_likes')[:1]

                top2_ans = []
                # for answer in answers:
                    # print('The parent answer - ', answer)
                answers_and_replies = [answer] + list(answer.get_descendants())
                # answers_and_replies = [answer] + list(answer.get_descendants().order_by('-timestamp'))
                answers_with_descendants.extend(answers_and_replies) 
                top2_ans.append(answer.pk)
                
                # assuming that above instead of sending the first 2 answers we have send the top 2 answers , now we want to send the rest of the answers excluding the above 2

                other_answers_with_descendants = []

                answers = question.answers.filter(parent=None).exclude(id__in=top2_ans)
                answers = answers.order_by('-timestamp')
                for answer in answers:
                    # print('This is what the pending answers are - ', answer)
                    print('The answer - ',answer,' The reports - ',answer.ans_reports.all().count())
                    if answer.ans_reports.all().count() < 5:
                        other_answers_and_replies = [answer] + list(answer.get_descendants())
                        other_answers_with_descendants.extend(other_answers_and_replies) 
                


                
                question_answers.append([question,answers_with_descendants, other_answers_with_descendants])

                context['question'] = question_answers
                print('The question answers are -', question_answers)
                print('This is the fuckin id i have -',ans_id, type(ans_id))

            except Answer.DoesNotExist:
                return None
            
        else:
            context['ans_id'] = ans_id
            context['highlight_answer'] = ans_id
            
            # context['question'] = question

            question_answers = [] # ['{question' : {answers}}]

            answers_with_descendants = []

            # answers = question.answers.filter(parent=None)
            # answers = answers.annotate(num_likes=Count('likes'))
            # answers = answers.order_by('-num_likes')[:1]

            top2_ans = []
            # for answer in answers:
                # print('The parent answer - ', answer)
            answers_and_replies = [answer] + list(answer.get_descendants())
            answers_with_descendants.extend(answers_and_replies) 
            top2_ans.append(answer.pk)
            
            # assuming that above instead of sending the first 2 answers we have send the top 2 answers , now we want to send the rest of the answers excluding the above 2

            other_answers_with_descendants = []

            answers = question.answers.filter(parent=None).exclude(id__in=top2_ans)
            answers = answers.order_by('-timestamp')
            for answer in answers:
                # print('This is what the pending answers are - ', answer)
                print('The answer - ',answer,' The reports - ',answer.ans_reports.all().count())
                if answer.ans_reports.all().count() < 5:
                    other_answers_and_replies = [answer] + list(answer.get_descendants())
                    other_answers_with_descendants.extend(other_answers_and_replies) 
            


            
            question_answers.append([question,answers_with_descendants, other_answers_with_descendants])

            context['question'] = question_answers
            print('The question answers are -', question_answers)

            
    except Answer.DoesNotExist:
        return HttpResponse('The question/answer you are looking for does not exist!')


    return render(request, "qna/quest.html", context)

def qna_payload(request, questions):
    try:
        
        question_answers = [] # ['{question' : {answers}}]

        for question in questions:
            # question_answers.append([question, question.answers.all()])
            # print('question - ', question)

            '''
            check if the question is already polled than don't show it to the user
            '''
            # skip_outer_loop = False
            # for poll in question.polls.all():
            #     if request.user in poll.polled.all():
            #         # print('The user has already polled this quest &&&&&&&&&&&&&&&')
            #         skip_outer_loop = True
            #         break  # exit the inner loop

            # if skip_outer_loop:
            #     continue  # skip the remaining iterations of the outer loop
            poll_status = question.is_already_polled(request.user)
            answers_with_descendants = []

            answers = question.answers.filter(parent=None).annotate(report_count=Count('ans_reports')).exclude(report_count__gt=10)
            answers = answers.annotate(num_likes=Count('likes'))
            answers = answers.order_by('-num_likes')[:1]

            top2_ans = []
            for answer in answers:
                # print('The parent answer - ', answer)
                
                answers_and_replies = [answer] + list(answer.get_descendants())
                answers_with_descendants.extend(answers_and_replies) 
                top2_ans.append(answer.pk)
            
            # assuming that above instead of sending the first 2 answers we have send the top 2 answers , now we want to send the rest of the answers excluding the above 2

            other_answers_with_descendants = []

            if not question.polls.all():
                answers = question.answers.filter(parent=None).exclude(id__in=top2_ans)
            else:
                answers = question.answers.filter(parent=None)
            answers = answers.order_by('-timestamp')
            for answer in answers:
                # print('This is what the pending answers are - ', answer)
                print('The answer - ',answer,' The reports - ',answer.ans_reports.all().count())
                if answer.ans_reports.all().count() < 5:
                    other_answers_and_replies = [answer] + list(answer.get_descendants())
                    other_answers_with_descendants.extend(other_answers_and_replies) 
            
            
            question_answers.append([question,answers_with_descendants, other_answers_with_descendants, poll_status])
    except Exception as e:
        print('The fuckin exci -', str(e))
    
    return question_answers
    
def compress_image(image):
    # Open the image using Pillow
    img = Image.open(image)

    # Convert RGBA image to RGB
    if img.mode == 'RGBA':
        img = img.convert('RGB')

    # Create a BytesIO buffer to store the compressed image
    compressed_buffer = BytesIO()

    # Compress the image and save it to the buffer
    img.save(compressed_buffer, format='JPEG', quality=70)

    # Rewind the buffer to the beginning
    compressed_buffer.seek(0)

    # Create a new Django File object from the buffer
    compressed_image = ContentFile(compressed_buffer.read(), name=image.name)

    return compressed_image

def compress_video(video_file):
    # Save the TemporaryFile to disk
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, video_file.name)
    with open(temp_file_path, 'wb+') as out:
        out.write(video_file.file.read())

    # Load the video clip from the file path
    video_clip = VideoFileClip(temp_file_path)

    # # check the length of the video in seconds

    # duration = video_clip.duration
    # print('The video is this long - ', duration)
    # if int(duration) > 300:
    #     compressed_video = None

    # Reduce the quality of the video
    reduced_quality_clip = video_clip.fx(fx.resize.resize, height=720)

    # Create a temporary file path for the compressed video
    compressed_file_path = os.path.join(temp_dir, 'compressed_' + video_file.name)

    # Write the compressed video to the file
    reduced_quality_clip.write_videofile(compressed_file_path, codec="libx264")

    # Read the compressed video into a BytesIO buffer
    with open(compressed_file_path, 'rb') as f:
        compressed_buffer = BytesIO(f.read())

    # Create an InMemoryUploadedFile from the buffer
    compressed_video = InMemoryUploadedFile(
        compressed_buffer,
        None,
        os.path.basename(video_file.name),
        video_file.content_type,
        compressed_buffer.tell(),
        None
    )

    # Set the file size of the compressed video
    compressed_video.size = compressed_buffer.tell()
    
    # Delete the original temporary file
    os.remove(temp_file_path)

    # Delete the compressed temporary file
    os.remove(compressed_file_path)

    return compressed_video


# def generate_thumbnail(video_file):
#     # Get the path of the video file
#     video_path = video_file.temporary_file_path()
    
#     # Create a path for the thumbnail
#     thumbnail_path = os.path.splitext(video_file.name)[0] + "_thumbnail.jpg"
    
#     # Use ffmpeg to extract a frame at the middle of the video
#     command = f"ffmpeg -i {video_path} -vf \"select=eq(n\\,{int(video_file.size / 2)})\" -vframes 1 {thumbnail_path}"
#     subprocess.run(command, shell=True, check=True)
    
#     # Read the thumbnail into a BytesIO object
#     with open(thumbnail_path, "rb") as thumbnail_file:
#         thumbnail_io = io.BytesIO(thumbnail_file.read())
    
#     # Create a Django ContentFile
#     thumbnail_content_file = ContentFile(thumbnail_io.getvalue(), thumbnail_path)
    
#     return thumbnail_content_file