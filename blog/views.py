from django.shortcuts import render, get_object_or_404
from .models import Post, Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import EmailPostForm, CommentForm,SearchForm
from django.core.mail import send_mail, EmailMultiAlternatives
from django.views.decorators.http import require_POST
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from taggit.models import Tag
from django.db.models import Count
from django.contrib.postgres.search import SearchVector


def post_search(request):
    form = SearchForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = Post.published.annotate(
            search=SearchVector('title', 'body'),
            ).filter(search=query)

    return render(request,
                'blog/post/search.html',
                {'form': form,
                'query': query,
                'results': results})




def post_list(request,tag_slug=None):
    post_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])
    paginator = Paginator(post_list, 1)  # Постраничная разбивка с 3 постами на страницу
    page_number = request.GET.get('page', 1)
    
    try:
        posts = paginator.page(page_number)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)  # Если page_number находится вне диапазона, показываем последнюю страницу
    except PageNotAnInteger:
        posts = paginator.page(1)
    
    return render(request, 'blog/post/list.html', {'posts': posts,'tag': tag})



def post_detail(request, year, month, day, post):

    post = get_object_or_404(Post, status=Post.Status.PUBLISHED, slug=post, publish__year=year, publish__month=month, publish__day=day) 
    # Список активных комментариев к этому посту
    comments = post.comments.filter(active=True)
    # Форма для комментариев пользователей
    form = CommentForm()

    # Список схожих постов
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids)\
                                  .exclude(id=post.id)   
    similar_posts = similar_posts.annotate(same_tags=Count('tags'))\
                                 .order_by('-same_tags','-publish')[:4]



    return render(request,'blog/post/detail.html', {'post': post,'comments': comments,'form': form,'similar_posts': similar_posts})


def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    sent = False
    if request.method == 'POST':
        form = EmailPostForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            my_subject = f"{cd['name']} recommends you read " \
                      f"{post.title}"
            html_message = render_to_string("blog/email.html")
            plain_message = strip_tags(html_message)
            #message = f"Read {post.title} at {post_url}\n\n f"{cd['name']}\'s comments: {cd['comments']}"
            message = EmailMultiAlternatives(
                subject = my_subject,
                body= plain_message,
                from_email= 'ramz1230777@gmail.com' ,
                to= [cd['to']]
            )
            message.attach_alternative(html_message, "text/html")
            message.send()
            #send_mail(subject, message, 'ramz1230777@gmail.com', [cd['to']])
            sent = True
    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post, 'form': form})

@require_POST
def post_comment(request,post_id):
    post=get_object_or_404(Post,id=post_id,status=Post.Status.PUBLISHED)
    comment=None
    # Комментарий был отправлен
    form=CommentForm(data=request.POST)
    if form.is_valid():
        # Создать объект класса Comment, не сохраняя его в базе данных
        comment = form.save(commit=False)
        # Назначить пост комментарию
        comment.post = post
        # Сохранить комментарий в базе данных
        comment.save()

    return render(request, 'blog/post/comment.html',  
                            {'post': post,
                            'form': form,
                            'comment': comment})
