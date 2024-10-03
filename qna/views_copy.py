from django.shortcuts import render, redirect
from django.http import HttpResponse
from qna.models import PublicChatRoom, Answer, Polls
import json
from django.db.models import Count
from django.contrib import messages
from account.models import Account

from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count



# Create your views here.
def pika_view(request):

    # if not request.user.is_authenticated:
    #     return redirect('login')

    if request.user.is_authenticated:
        user = request.user
        user.update_last_activity()

    context = {}

    question_answers = [] # ['{question' : {answers}}]

    # questions = PublicChatRoom.objects.all()
    questions = PublicChatRoom.objects.all().order_by('-timestamp')
    # questions = PublicChatRoom.objects.all().exclude(answers__user = request.user)
    questions = questions.order_by('-timestamp')
    

    for question in questions:
        # question_answers.append([question, question.answers.all()])
        # print('question - ', question)

        '''
        check if the question is already polled than don't show it to the user
        '''
        skip_outer_loop = False
        for poll in question.polls.all():
            if request.user in poll.polled.all():
                # print('The user has already polled this quest &&&&&&&&&&&&&&&')
                skip_outer_loop = True
                break  # exit the inner loop

        if skip_outer_loop:
            continue  # skip the remaining iterations of the outer loop

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
        


        
        question_answers.append([question,answers_with_descendants, other_answers_with_descendants])
            
        
   
    context['question_top2_answers'] = question_answers

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
                    print('this is the before ans - ')
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