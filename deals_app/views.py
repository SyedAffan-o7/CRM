from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from deals_app.models import Deal


@login_required
def deal_list(request):
    """List all deals"""
    if request.user.is_superuser:
        deals = Deal.objects.all()
    else:
        deals = Deal.objects.filter(created_by=request.user)

    return render(request, 'crm_app/deal_list.html', {
        'deals': deals,
        'title': 'Deals'
    })


@login_required
def deal_add(request):
    """Add new deal"""
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Deal.objects.create(
                deal_name=name,
                deal_stage=request.POST.get('stage', 'prospecting'),
                deal_value=request.POST.get('value', 0) or 0,
                created_by=request.user
            )
            messages.success(request, 'Deal created successfully.')
            return redirect('crm_app:deal_list')

    return render(request, 'crm_app/deal_form.html', {'title': 'Add Deal'})


@login_required
def deal_detail(request, pk):
    """Deal detail view"""
    deal = get_object_or_404(Deal, pk=pk)
    return render(request, 'crm_app/deal_detail.html', {
        'deal': deal,
        'title': f'Deal: {deal.deal_name}'
    })


@login_required
def deal_edit(request, pk):
    """Edit deal"""
    deal = get_object_or_404(Deal, pk=pk)
    if request.method == 'POST':
        deal.deal_name = request.POST.get('name', deal.deal_name)
        deal.deal_stage = request.POST.get('stage', deal.deal_stage)
        deal.deal_value = request.POST.get('value', deal.deal_value)
        deal.save()
        messages.success(request, 'Deal updated successfully.')
        return redirect('crm_app:deal_detail', pk=pk)

    return render(request, 'crm_app/deal_form.html', {
        'deal': deal,
        'title': f'Edit Deal: {deal.deal_name}'
    })
