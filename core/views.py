import requests
from django.views.generic import View, TemplateView

from django.views.generic import ListView,CreateView, UpdateView,DeleteView,DetailView
from django.contrib.auth import get_user_model

from .models import  User,Franchise,State,District
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q,Sum
from django.http import HttpResponse
from django.views import generic
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction, IntegrityError
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import Role
from .forms import  RoleForm , FranchiseForm
from django.contrib.auth.mixins import PermissionRequiredMixin



# Base Views  for create and Update c bndsjjs


class BaseCreateView(PermissionRequiredMixin, generic.CreateView):
    template_name = None
    model = None
    form_class = None
    success_url = None

    def get_permission_required(self):
        meta = self.model._meta
        app_name, table_name = meta.app_label, meta.model_name
        return [f'{app_name}.add_{table_name}']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        meta = self.model._meta

        context['title'] = f'Add New {meta.verbose_name}'
        context['cancel_url'] = self.success_url
        context['meta'] = meta
        return context
    
    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)


class BaseUpdateView(PermissionRequiredMixin, generic.UpdateView):
    template_name = None
    model = None
    form_class = None
    success_url = None

    def get_permission_required(self):
        meta = self.model._meta
        app_name, table_name = meta.app_label, meta.model_name
        return [f'{app_name}.change_{table_name}']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        meta = self.model._meta

        context['title'] = f'Update {meta.verbose_name}'
        context['cancel_url'] = self.success_url
        context['meta'] = meta
        return context
    
    
    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)




class BaseListView(PermissionRequiredMixin, generic.ListView):
    template_name = None
    model = None
    paginate_by = 10
    context_object_name = 'objects'
    add_text = None
    add_url = None

    def get_permission_required(self):
        meta = self.model._meta
        app_name, table_name = meta.app_label, meta.model_name
        return [f'{app_name}.view_{table_name}']
    
    def get_queryset(self):
        queryset = super().get_queryset()

        show_record = self.request.GET.get('show_record', self.paginate_by)
        self.paginate_by = int(show_record)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        meta = self.model._meta

        show_record = int(self.request.GET.get('show_record', self.paginate_by))
        current_page = int(self.request.GET.get('page', 1))
        sort_by = self.request.GET.get('sort_by', 'id')
        total_count = self.get_queryset().count()
        start_count = current_page * self.paginate_by - self.paginate_by + 1
        end_count = current_page * self.paginate_by
        
        context['objects_count'] = total_count
        context['start_count'] = start_count
        context['end_count'] = end_count if end_count <= total_count else total_count
        context['sort_by'] = sort_by
        context['show_record'] = show_record

        context['meta'] = meta
        context['add_text'] = self.add_text if not self.add_text is None else f'Add {meta.verbose_name}'
        context['add_url'] = self.add_url

        return context


















    # Roles lisitng 
class RolesList(ListView):
    model = Role
    template_name = "core/roles/list.html"
    context_object_name = "roles"
    paginate_by = 10  
    def get_paginate_by(self, queryset):
        """Allow user to select 10/25/50/100 per page."""
        page_size = self.request.GET.get('page_size')
        if page_size in ['10', '25', '50', '100']:
            return int(page_size)
        return self.paginate_by
    def get_queryset(self):
        qs = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            qs = qs.filter(name__icontains=search_query)
        return qs
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']

        # Build a sliding window of pages around the current page
        start_index = max(page_obj.number - 3, 1)
        end_index = min(page_obj.number + 3, page_obj.paginator.num_pages) + 1
        context['page_range'] = range(start_index, end_index)
        # Pass the current search term to the template for re-populating the search input
        context['search_query'] = self.request.GET.get('search', '')
        return context
    
class RoleCreateView(generic.CreateView):
    model = Role
    form_class = RoleForm
    template_name = 'core/roles/create.html'  # Adjust the template path as needed
    success_url = reverse_lazy('roles')  # Change this to your desired URL

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Load all content types except for a fixed set (as in case 2)
        content_types = ContentType.objects.all().exclude(id__in=(1, 2, 3, 4, 5))
        content_types = content_types.order_by('pk').prefetch_related('permission_set')
        context['content_types'] = content_types
        # Set a cancel URL, e.g., back to the role list view
        context['cancel_url'] = reverse_lazy('roles')
        return context

    @transaction.atomic
    def form_valid(self, form):
        # Save the role instance (which will set the slug based on name)
        response = super().form_valid(form)
        role = self.object

        # Process group permissions
        group_permissions = self.request.POST.getlist('permissions')
        permissions = Permission.objects.filter(id__in=group_permissions)
        
        # Since there is no organization/school, use the role name directly
        group_name = role.name  
        group, created = Group.objects.get_or_create(name=group_name)
        # Update the group’s permissions
        group.permissions.set(permissions)
        return response


class RoleUpdateView(generic.UpdateView):
    model = Role
    form_class = RoleForm
    template_name = 'core/roles/create.html'  # Re-using the same template for update
    success_url = reverse_lazy('roles')  # Change this as needed

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = self.object
        
        # Retrieve the related group using the role name
        group_name = role.name
        group = get_object_or_404(Group, name=group_name)
        
        # Load content types and current group permissions
        content_types = ContentType.objects.all().exclude(id__in=(1, 2, 3, 4, 5))
        content_types = content_types.order_by('pk').prefetch_related('permission_set')
        current_permissions = group.permissions.all().order_by('content_type_id')
        
        context['content_types'] = content_types
        context['current_permissions'] = current_permissions
        context['cancel_url'] = self.get_success_url()  # Here you may adjust the cancel behavior if needed
        return context

    @transaction.atomic
    def form_valid(self, form):
        # Save the updated role instance
        role = form.save()
        
        # Update the associated group's permissions
        group_permissions = self.request.POST.getlist('permissions')
        permissions = Permission.objects.filter(id__in=group_permissions)
        group_name = role.name
        group, created = Group.objects.get_or_create(name=group_name)
        group.permissions.set(permissions)
        return redirect(self.get_success_url())

    
    
    
# Users Lisitng



class UsersList(ListView):
    template_name = "core/users/list.html"
    context_object_name = "users"
    queryset = User.objects.all()
    paginate_by = 10  

    def get_paginate_by(self, queryset):
        """Allow user to select 10/25/50/100 per page."""
        page_size = self.request.GET.get('page_size')
        if page_size in ['10', '25', '50', '100']:
            return int(page_size)
        return self.paginate_by

    def get_queryset(self):
        qs = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            qs = qs.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']
        # Build a sliding window of pages around the current page
        start_index = max(page_obj.number - 3, 1)
        end_index = min(page_obj.number + 3, page_obj.paginator.num_pages) + 1
        context['page_range'] = range(start_index, end_index)
        # Pass the current search term to the template for re-populating the search input
        context['search_query'] = self.request.GET.get('search', '')
        return context
class AddUsers(TemplateView):
    template_name = "core/users/create.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = Role.objects.all().order_by('name')
        return context


@csrf_exempt  # In production, pass the CSRF token via AJAX headers
@require_POST
def ajax_add_user(request):
    try:
        data = json.loads(request.body)
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        username = data.get('username')
        email = data.get('email')
        role = data.get('role')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        # New fields
        designation = data.get('designation', '')
        mobile = data.get('mobile', '')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON data.'}, status=400)

    # Check required fields
    if not all([first_name, last_name, username, email, password, confirm_password]):
        return JsonResponse({'error': 'Missing required fields.'}, status=400)

    # Verify that the password and confirm password match
    if password != confirm_password:
        return JsonResponse({'error': 'Passwords do not match.'}, status=400)

    try:
        # Create the user using the provided password and new fields
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            designation=designation,  # new field
            mobile_number=mobile      # new field (mapped from "mobile")
        )
    except Exception as e:
        return JsonResponse({'error': f'User creation failed: {str(e)}'}, status=400)

    try:
        # Optionally, assign the user to a group and mark as staff
        staff_group, created = Group.objects.get_or_create(name=role)
        user.groups.add(staff_group)
        if role.lower() in ['admin', 'manager', 'staff']:
            user.is_staff = True
        user.save()
    except Exception as e:
        return JsonResponse({'error': f'Failed to assign staff group: {str(e)}'}, status=400)

    return JsonResponse({
        'message': 'User created successfully',
        'user_id': user.id,
        'redirect_url': reverse('users')  # update to your URL pattern name if needed
    })
    

class EditUsers(TemplateView):
    template_name = "core/users/create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch the user you want to edit
        user_id = self.kwargs.get('pk')
        user = get_object_or_404(User, pk=user_id)
        
        # Return basic user info and roles so the template can pre-fill fields
        context['edit_user'] = user
        context['roles'] = Role.objects.all().order_by('name')
        return context

@csrf_exempt
@require_POST
def ajax_edit_user(request, pk):
    try:
        # Find the existing user
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found.'}, status=404)

    try:
        data = json.loads(request.body)
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        role = data.get('role')
        print(role)
        # role = data.get('role', 'Staff')  # if you want to update role
    except Exception:
        return JsonResponse({'error': 'Invalid JSON data.'}, status=400)

    if not all([first_name, last_name, email]):
        return JsonResponse({'error': 'Missing required fields.'}, status=400)

    # Update user fields
    try:
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        new_password = data.get('password')
        confirm_password = data.get('confirm_password')

        if new_password or confirm_password:
            if new_password != confirm_password:
                return JsonResponse({'error': 'Passwords do not match.'}, status=400)
            user.set_password(new_password)
            user.save()
    except Exception as e:
        return JsonResponse({'error': f'User update failed: {str(e)}'}, status=400)

    # (Optional) Update user’s groups, roles, etc.
    try:
        staff_group, _ = Group.objects.get_or_create(name=role)
        user.groups.clear()
        user.groups.add(staff_group)
        user.is_staff = True
        user.save()
    except Exception as e:
        return JsonResponse({'error': f'Failed to assign staff group: {str(e)}'}, status=400)

    return JsonResponse({
        'message': 'User updated successfully',
        'user_id': user.id,
        'redirect_url': reverse('users')
    })    
#supplier 
from django.db.models import Q


#Franchise


# class FranchiseList(ListView):
#     model = Franchise
#     template_name = "franchise/list.html"
#     context_object_name = "franchises"
#     paginate_by = 10  

#     def get_queryset(self):
#         queryset = super().get_queryset()
#         q = self.request.GET.get('q', '')
#         if q:
#             queryset = queryset.filter(
#                 Q(name__icontains=q) |
#                 Q(owner__icontains=q) |
#                 Q(gstid__icontains=q) |
#                 Q(email__icontains=q) |
#                 Q(city__icontains=q)
#             )
        
#         # Order descending by the annotated total_due field.
     
#         return queryset

#     def get_paginate_by(self, queryset):
#         """Allow user to select 10/25/50/100 per page."""
#         page_size = self.request.GET.get('page_size')
#         if page_size in ['10', '25', '50', '100']:
#             return int(page_size)
#         return self.paginate_by

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         page_obj = context['page_obj']
#         franchises = Franchise.objects.all()
#         total_students = franchises.aggregate(total=Sum('no_of_students'))['total'] or 0
#         # Build a sliding window of pages around the current page
#         start_index = max(page_obj.number - 3, 1)
#         end_index = min(page_obj.number + 3, page_obj.paginator.num_pages) + 1
#         context['page_range'] = range(start_index, end_index)
#         # Pass the current search term to the template so it can be re-used in the search field.
#         context['search_query'] = self.request.GET.get('q', '')
#         context['total_students']= total_students
        
#         return context
    


# Franchise (API Integration)
class FranchiseList(ListView):
    model = Franchise
    template_name = "franchise/list.html"
    context_object_name = "franchises"
    paginate_by = 10

    API_URL = "https://main.aicrosswindabacus.com/franchise/all/"

    def get_queryset(self):
        search_query = self.request.GET.get("q", "").strip()

        try:
            response = requests.get(self.API_URL, timeout=15)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list):
                raise ValueError("Expected the API to return a JSON list.")

            franchises = [
                {
                    "id": item.get("id"),
                    "name": item.get("name") or "",
                    "franchise_code": item.get("franchise_code") or "",
                    "franchise_location": item.get("franchise_location") or "",
                }
                for item in data
                if isinstance(item, dict)
            ]

            if search_query:
                query = search_query.casefold()
                franchises = [
                    item for item in franchises
                    if query in item["name"].casefold()
                    or query in item["franchise_code"].casefold()
                    or query in item["franchise_location"].casefold()
                ]

            return franchises

        except (requests.RequestException, ValueError) as exc:
            self.api_error = str(exc)
            return []

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get("page_size")
        if page_size in ["10", "25", "50", "100"]:
            return int(page_size)
        return self.paginate_by

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["search_query"] = self.request.GET.get("q", "")
        context["total_students"] = 0
        context["api_error"] = getattr(self, "api_error", None)

        return context



class FranchiseCreateView(CreateView):
    model = Franchise
    form_class = FranchiseForm
    template_name = "franchise/create.html"
    success_url = reverse_lazy('franchise')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
       
        User = get_user_model()
        context['users'] = User.objects.all()
        return context

    def form_valid(self, form):
      
        response = super().form_valid(form)

        assigned_supervisor_id = self.request.POST.get('assigned_supervisor')
       
        return response 


class FranchiseUpdateView(UpdateView):
    model = Franchise
    form_class = FranchiseForm
    template_name = "franchise/create.html"
    success_url = reverse_lazy('franchise')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass available supervisors to the template.
        User = get_user_model()
        context['users'] = User.objects.all()
        # Optionally pass the current supervisor's ID so that the dropdown can pre-select it.
        if hasattr(self.object, 'supervision_assignment') and self.object.supervision_assignment.supervisor:
            context['assigned_supervisor'] = self.object.supervision_assignment.supervisor.pk
        else:
            context['assigned_supervisor'] = ''
        return context

    def form_valid(self, form):
        # Save the Franchise instance first.
        response = super().form_valid(form)
        # Retrieve the selected supervisor from the POST data.
        assigned_supervisor_id = self.request.POST.get('assigned_supervisor')
        User = get_user_model()
        supervisor = None
        if assigned_supervisor_id:
            try:
                supervisor = User.objects.get(pk=assigned_supervisor_id)
            except User.DoesNotExist:
                supervisor = None
        
       
        return response












    
class FranchiseDeleteView(DeleteView):
    model = Franchise
    template_name = 'franchise/confirm_delete.html'  
    success_url = reverse_lazy('franchise')
    
    
class FranchiseDetailView(DetailView):
    model = Franchise
    template_name = 'franchise/detail.html'
    context_object_name = 'supplier' 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        franchise = self.get_object()
       
        orders_list = franchise.sell_orders.all().order_by('-date')
        if not self.request.user.has_perm('inventory.view_quantity_dependent'):
            orders_list = orders_list.filter(items__item__quantity_dependent=True).distinct()
       
        page_size = self.request.GET.get('page_size')
        if page_size in ['10', '25', '50', '100']:
            page_size = int(page_size)
        else:
            page_size = 10

        paginator = Paginator(orders_list, page_size)
        page_number = self.request.GET.get('page')
        try:
            orders = paginator.page(page_number)
        except PageNotAnInteger:
            orders = paginator.page(1)
        except EmptyPage:
            orders = paginator.page(paginator.num_pages)

        context['purchase_orders'] = orders

        
        start_index = max(orders.number - 3, 1)
        end_index = min(orders.number + 3, orders.paginator.num_pages) + 1
        context['page_range'] = range(start_index, end_index)
       
        return context
    
