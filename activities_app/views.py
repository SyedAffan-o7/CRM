from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from activities_app.models import ActivityLog
from crm_app.forms import ActivityLogForm


@login_required
def activity_list(request):
    """List all activities"""
    if request.user.is_superuser:
        activities = ActivityLog.objects.all()
    else:
        activities = ActivityLog.objects.filter(user=request.user)

    return render(request, 'crm_app/activity_list.html', {
        'activities': activities,
        'title': 'Activities'
    })


@login_required
def activity_add(request):
    """Add new activity"""
    if request.method == 'POST':
        form = ActivityLogForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            # Ensure the activity is attributed to the current user
            setattr(activity, 'user', getattr(activity, 'user', None) or request.user)
            activity.save()
            messages.success(request, 'Activity logged successfully.')
            return redirect('crm_app:activity_list')
    else:
        form = ActivityLogForm()

    return render(request, 'crm_app/activity_form.html', {
        'title': 'Log Activity',
        'form': form,
    })
