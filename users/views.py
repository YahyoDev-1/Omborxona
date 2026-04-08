from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout


# Create your views here.

class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        user = authenticate(
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        if user is not None:
            login(request, user)
            messages.success(request, "You have successfully logged in")
            return redirect('sections')
        messages.error(request, "Username or password is incorrect")
        return render(request, 'login.html')


def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect('login')

    return render(request, 'logout-confirmation.html')
