from django.shortcuts import render, redirect
from django.http import HttpResponse
from confessions.models import CPublicChatRoom, CAnswer
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
import uuid
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponseNotFound



# Create your views here.
def pikac_view(request):

    print('confesion is gettin called!')

    # if not request.user.is_authenticated:
    #     return redirect('login')

    if request.user.is_authenticated:
        user = request.user
        user.update_last_activity()

    context = {}
    

    # question_answers = [] # ['{question' : {answers}}]

    # questions = PublicChatRoom.objects.all()
    questions = CPublicChatRoom.objects.all().order_by('-timestamp')
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
    # print('this is the questions page - ',current_page_questions)
    my_list = qna_payload(request, current_page_questions)

    # print(my_list)


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

    # print('this is the questions page - ',current_page_questions)
    my_list = qna_payload(request, current_page_questions)

    # print(my_list)
    context['question_top2_answers'] = my_list

    if request.GET.get('action') == 'new_ques':
        # If it's an AJAX request, return JSON response
        print('the ajax request is getting processed')
       
        data = {
            'html': render_to_string('confessions/question_partialc.html', {'question_top2_answers': my_list,'the_questions': questions_page}, request=request),
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
    context['is_active'] = 'confessions'

    return render(request, "confessions/questions.html", context)

def create_post_view(request):

    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':

        user = request.user
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)

        # Query for confessions sent by the user in the past 24 hours
        sent_requests = CPublicChatRoom.objects.filter(
            owner=user,
            timestamp__gte=twenty_four_hours_ago
        ).order_by('-timestamp')

        confessions_count = sent_requests.count()
        print('this is the friend req count - ', confessions_count)
        if confessions_count > 10:
            messages.warning(request, 'You can only send 10 Tagged confessions in 24 hrs.')
            return redirect('confessions:create-postc')

        question = request.POST.get('question')
        # taggiemail = request.POST.get('taggiemail')
        taggiemail = request.POST.get('taggiemail')
        taggiemode = request.POST.get('selecti')
        taggiename = request.POST.get('taggiename')

        print('the taggie ode - ',taggiemode)
        # print('the taggie info - ',taggieinfo)
        

        # poll1 = request.POST.get('poll1')
        # poll2 = request.POST.get('poll2')
        # poll3 = request.POST.get('poll3')
        # poll4 = request.POST.get('poll4')

        
        if taggiemail:
            confesser_id = my_unique_confession_id(request.user)
            print('This is the confesser id - ', confesser_id)
            roomv = CPublicChatRoom(question = question, owner = user, confesserid = confesser_id)
            

            # generate a unique token so that the taggie can reply back on this confession 
            confession_token = str(uuid.uuid4())
            roomv.taggie_token = confession_token
            roomv.taggie_name = taggiename
            roomv.is_tagged = True

            if taggiemail:
                # later on filter whether its abusive or not but for now just send it -
                '''
                Here we gotta send an email to the taggie at the given info
                ''' 
                roomv.taggie_info = taggiemail
                roomv.taggie_email = taggiemode
                roomv.save()
            

            answer = CAnswer(question = roomv, user = user, content=question, confesserid = confesser_id)
            answer.save()

            # how to generate the link
            mi_tukon = f"https://mystranger.in/confessions/question/{roomv.pk}/?question=true&taggie_token={confession_token}"

            roomv.taggie_link = mi_tukon
            roomv.save()
            
                # save the info into the confesions 
                

        #     #This means this questions has polls in it

        #     polls_list = [poll1,poll2,poll3,poll4]
        #     counter = 0
        #     for poll in polls_list:
        #         if poll:
        #             counter += 1
        #     if counter <2:
        #         messages.warning(request, 'Please add atleast two poles or add none...')
        #         return redirect('confessions:create-post')
        #     roomv = CPublicChatRoom(question = question, owner = user)
        #     roomv.save()
        #     # for poll in polls_list:
        #     #     if poll:
        #     #         pollva = Polls(question = roomv, option=poll)
        #     #         pollva.save()
        
        else:
            confesser_id = my_unique_confession_id(request.user)
            print('This is the confesser id - ', confesser_id)
            # now we want the taggie info
            roomv = CPublicChatRoom(question = question, owner = user, confesserid = confesser_id)
            roomv.save()
            answer = CAnswer(question = roomv, user = user, content=question, confesserid = confesser_id)
            answer.save()
            
        return redirect('confessions:pikac')

    return render(request, "confessions/create_question.html")

def minichat_view(request, *args, **kwargs):
    return render(request, "confessions/confessionsroom.html")


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
                answer = CAnswer.objects.get(pk=id)
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
                answer = CAnswer.objects.get(pk=id)
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
                question = CPublicChatRoom.objects.get(pk=id)
                print('This question is getting deleted - ', question)

                if question.owner == request.user or question.taggie == request.user:
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
                answer = CAnswer.objects.get(pk=id)
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
                answer = CAnswer.objects.get(pk=id)
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
        

        # if request.POST.get('action') == 'poll-selected':

        #     print('poll selected request arrived')
        #     id = request.POST.get('poll-id')

        #     try:
        #     #     answer = Answer.objects.get(pk=id)
        #     #     answer.remove_like(request.user)
        #         poll = Polls.objects.get(id=id)
        #         poll.add_user(request.user)

        #         # now we wanna get a json with poll id and its percentage

        #         # for that first gonna fetch the question

        #         question = poll.question
        #         # print(question)

        #         empy_dict = {}
        #         total_polled = 0
        #         for poll in question.polls.all():
        #             total_polled += poll.polled.all().count()
                
        #         for poll in question.polls.all():
        #             empy_dict[poll.id] = round((poll.polled.all().count() / total_polled) * 100, 1)
                
        #         print('This is the empy dict with all the data regarding this ques and its polls - ', empy_dict)


        #         ac_poll_id = None
        #         try:
        #             if request.POST.get('account') == 'yup':
        #                 account_id = request.POST.get('account_id')
        #                 account = Account.objects.get(id=account_id)
        #                 for poll in question.polls.all():
        #                     if account in poll.polled.all():
        #                         ac_poll_id = poll.id
        #                         break
        #         except Exception as e:
        #             print('Error fetching what other user polled - ',str(e))


        #         response_data = {
        #         'status' : 'got_data',
        #         'response' : empy_dict,
        #         'total_polls' : total_polled,
        #         'ac_poll_id' : ac_poll_id,
                
        #     }
                
        #     except Exception as e:
        #         print('error fetching the data - ' , str(e))
        #         response_data = {
        #         'status' : 'error',
        #         'message': str(e),
        #     }
            
            
        #     return HttpResponse(json.dumps(response_data), content_type="application/json")


        try:
            
            question_id = request.POST.get('question-id')
            print('The question id is -', question_id)
            content = request.POST.get('id_chat_message_input')
            user = request.user

            try:
                question = CPublicChatRoom.objects.get(pk=question_id)

                parent_id = request.POST.get('answer-id')
                print('The parent id is - ', parent_id)
                if parent_id:
                    if content:
                        parent = CAnswer.objects.get(pk=parent_id)
                        answer = CAnswer(question = question, user = user, content=content, parent=parent)
                        answer.save()
                        if answer.question.owner == request.user:
                            name = "Confesser"
                        elif answer.question.taggie == request.user:
                            name = "Taggie"
                        else:
                            name = "Stranger"
                        response_data = {
                            'status' : 'Replied',
                            'message': 'Your reply has been added.',
                            'name' : name,
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
                        answer = CAnswer(question = question, user = user, content=content)
                        answer.save()
                        if answer.question.owner == request.user:
                            name = "Confesser"
                        elif answer.question.taggie == request.user:
                            name = "Taggie"
                        else:
                            name = "Stranger"
                        print('this is the ans - ', answer)
                        response_data = {
                            'status' : 'Answered',
                            'message': 'Your answer has been added.',
                            'name' : name,
                            'content' : content,
                            'domain' : user.university_name,
                            'nodeId' : answer.id,
                            
                        }
                    else:
                        response_data = {
                            'status' : 'empty_msg',

                        }

            except CPublicChatRoom.DoesNotExist:
                print('Error - question/answer doesn not exist!')

        except Exception as e:
            print('The addAnswer/reply exception is - ', str(e))
            response_data = {
                'status' : 'error',
                'message': str(e),
            }

    return HttpResponse(json.dumps(response_data), content_type="application/json")


def cworking_view(request,*args, **kwargs):
    return render(request, 'confessions/cworking.html')

def search_view(request,*args, **kwargs):
    if 'q' in request.GET:
        query = request.GET['q']
        try:
            # Assuming YourModel has a field named 'unique_id'
            if request.user.is_authenticated:
                confession = CPublicChatRoom.objects.filter(taggie_token=query).first()
                print('the confession is this -',confession)
                if confession:
                    confession.taggie = request.user
                    confession.save()
                    redirect_url = f'/confessions/question/{confession.id}/?question=true&taggie_token={query}'
                    print('the redirect url - ', redirect_url)
                    return redirect(redirect_url)
                else:
                    return HttpResponseNotFound('invalid token or the confesser has deleted the confession.')
            else:
                messages.warning(request, 'You need to login in order to reply to this confession.')
                confession = CPublicChatRoom.objects.filter(taggie_token=query).first()
                if confession:
                    redirect_url = f'/confessions/question/{confession.id}/?question=true'
                    return redirect(redirect_url)
                else:
                    return HttpResponseNotFound('invalid token or the confesser has deleted the confession.')
        except CPublicChatRoom.DoesNotExist:
            # Unique ID not found, show alert or render a page with an alert
            return HttpResponseNotFound('Invalid Token')
    return redirect("confessions:pikac")


def show_ques_view(request,*args, **kwargs):

    ans_id = kwargs.get('ans_id')
    
    context = {}

    if request.user.is_authenticated:
        user = request.user
        user.update_last_activity()

    try:
        
        is_ques = request.GET.get('question')
        taggie_token = request.GET.get('taggie_token')
        if taggie_token:
            if request.user.is_authenticated:
                try:
                    confession = CPublicChatRoom.objects.filter(taggie_token=taggie_token).first()
                    if confession:
                        confession.taggie = request.user
                        confession.save()
                except Exception as e:
                    return HttpResponse('invalid token or the confesser has deleted the confession')
            else:
                messages.warning(request, 'You need to login in order to reply to this confession.')
                confession = CPublicChatRoom.objects.filter(taggie_token=taggie_token).first()
                if confession:
                    redirect_url = f'/confessions/question/{confession.id}/?question=true'
                    return redirect(redirect_url)
                else:
                    return(HttpResponse('invalid token or the confesser has deleted the confession.'))
            
        print('This is the tukon - ', taggie_token)
        if not is_ques:
            answer = CAnswer.objects.get(pk=ans_id)
        else:
        # now check if its a question
            try:
                question = CPublicChatRoom.objects.get(pk=ans_id)
                # answer = question.Canswers.filter(parent=None).annotate(report_count=Count('ans_reports')).exclude(report_count__gt=10)
                # answer = answer.annotate(num_likes=Count('likes'))
                # answer = answer.order_by('-num_likes')[:1].first()
                confessor_id = question.confesserid
                answers = question.Canswers.filter(parent=None, confesserid = confessor_id).annotate(report_count=Count('ans_reports')).exclude(report_count__gt=5)

                answer = answers.order_by('timestamp')[:1].first()
                
            except:
                return HttpResponse('The question/answer you are looking for does not exist! or is deleted!')
            
        ques_id = answer.question.id
        question = CPublicChatRoom.objects.get(pk=ques_id)

        # now gotta check whether this answer is a answer or a reply
        if answer.parent:
            context['ans_id'] = int(ans_id)
            context['highlight_reply'] = int(ans_id)

            try:
                child_node = CAnswer.objects.get(id=ans_id)
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

                answers = question.Canswers.filter(parent=None)
                answers = answers.annotate(num_likes=Count('likes'))
                answers = answers.order_by('-num_likes')[:1]

                top2_ans = []
                # for answer in answers:
                    # print('The parent answer - ', answer)
                answers_and_replies = [answer] + list(answer.get_descendants())
                # answers_and_replies = [answer] + list(answer.get_descendants().order_by('-timestamp'))
                answers_with_descendants.extend(answers_and_replies) 
                top2_ans.append(answer.pk)
                
                # assuming that above instead of sending the first 2 answers we have send the top 2 answers , now we want to send the rest of the answers excluding the above 2

                other_answers_with_descendants = []

                answers = question.Canswers.filter(parent=None).exclude(id__in=top2_ans)
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

            except CAnswer.DoesNotExist:
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

            answers = question.Canswers.filter(parent=None).exclude(id__in=top2_ans)
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

            
    except CAnswer.DoesNotExist:
        return HttpResponse('The question/answer you are looking for does not exist!')


    return render(request, "confessions/quest.html", context)

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

            answers_with_descendants = []

            confessor_id = question.confesserid
            answers = question.Canswers.filter(parent=None, confesserid = confessor_id).annotate(report_count=Count('ans_reports')).exclude(report_count__gt=5)

            answers = answers.order_by('timestamp')[:1]

            top2_ans = []
            for answer in answers:
                # print('The parent answer - ', answer)
                
                answers_and_replies = [answer] + list(answer.get_descendants())
                answers_with_descendants.extend(answers_and_replies) 
                top2_ans.append(answer.pk)
            
            # assuming that above instead of sending the first 2 answers we have send the top 2 answers , now we want to send the rest of the answers excluding the above 2

            other_answers_with_descendants = []

         
            answers = question.Canswers.filter(parent=None).exclude(id__in=top2_ans)
            # answers = question.Canswers.filter(parent=None)
            answers = answers.order_by('-timestamp')
            for answer in answers:
                # print('This is what the pending answers are - ', answer)
                print('The answer - ',answer,' The reports - ',answer.ans_reports.all().count())
                if answer.ans_reports.all().count() < 5:
                    other_answers_and_replies = [answer] + list(answer.get_descendants())
                    other_answers_with_descendants.extend(other_answers_and_replies) 
            
            
            question_answers.append([question,answers_with_descendants, other_answers_with_descendants])
    except Exception as e:
        print('The fuckin exci -', str(e))
    
    return question_answers
    

# This function is going to fetch the unique confession id of this user or if that id does not already exist than it is going to create one

def my_unique_confession_id(user):
    try:
        confesser_idi = user.confesser_id
        if confesser_idi and confesser_idi != "None":
            return confesser_idi
        else:
            # This means the id doesn't exist so create a unique one
            generated_uuid = uuid.uuid4()
            uuid_string = str(generated_uuid)[:8]

            # now we are checking if this id already exists or not 
            try:
                if user.confession_id == uuid_string:
                    generated_uuid = uuid.uuid4()
                    uuid_string = str(generated_uuid)[:8]
            except Exception as e:
                pass
            
            # this means uuid is kinda unique so add the uuid to account
            # my_ac = Account.objects.filter(user=user).first()
            my_ac = user
            my_ac.confesser_id = uuid_string
            my_ac.save()
            return uuid_string

    except Exception as e:
        print('error fetching confession id - ', str(e))