# Django imports
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Sum
from django.http import HttpResponseRedirect
from django.forms import modelformset_factory
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from django.core.mail import send_mail
from datetime import datetime
from django.http import JsonResponse

# Models and Forms
from .models import Product, Cart, CartItem, Category, Order, OrderItem, UserProfile
from .forms import UserRegisterForm, UserProfileForm, UserUpdateForm, ProfileImageForm, ChatForm

# External Libraries
from decimal import Decimal
import face_recognition
import openai
import os
import stripe
from dotenv import load_dotenv

# Langchain imports
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Charger la clé API d'OpenAI depuis le fichier .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def chatbot_view(request):
    form = ChatForm(request.POST or None)
    chat_history = request.session.get('chat_history', [])
    avatar_user = request.session.get('avatar_user', None)
    avatar_assistant = request.session.get('avatar_assistant', None)

    # Ajouter un message de bienvenue si l'historique est vide
    if not chat_history:
        welcome_message = {
            'role': 'AI',
            'content': f"Bienvenue, {request.user.username} ! Comment puis-je vous aider aujourd'hui ?"
        }
        chat_history.append(welcome_message)
        request.session['chat_history'] = chat_history

    # Récupérer l'avatar utilisateur
    if not avatar_user:
        user_profile = get_object_or_404(UserProfile, user=request.user)
        avatar_user = user_profile.face_id.url if user_profile.face_id else '/static/images/default-avatar.jpg'
        request.session['avatar_user'] = avatar_user

    # Récupérer l'avatar de l'assistant
    if not avatar_assistant:
        avatar_assistant = '/static/images/assistant.jpg'
        request.session['avatar_assistant'] = avatar_assistant

    # Récupérer les données de l'utilisateur
    orders = Order.objects.filter(user=request.user)
    order_items = OrderItem.objects.filter(order__user=request.user)
    cart = Cart.objects.filter(user=request.user).first()
    cart_items = CartItem.objects.filter(cart=cart) if cart else []
    categories = Category.objects.all()
    list_products = Product.objects.all()

    # Si la requête est AJAX
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        message = request.POST.get('message', '')
        if message:
            chat_history.append({'role': 'Human', 'content': message})

            # Préparer les informations personnelles pour le prompt
            personal_info = {
                "orders": orders,
                "order_items": order_items,
                "cart": cart,
                "cart_items": cart_items,
                "categories": categories,
                "list_products": list_products,
            }

            try:
                ai_response = retrieve_response(message, chat_history, personal_info)
                chat_history.append({'role': 'AI', 'content': ai_response})
            except Exception as e:
                ai_response = "Erreur de connexion avec l'API. Merci de réessayer plus tard."
                chat_history.append({'role': 'AI', 'content': ai_response})

            request.session['chat_history'] = chat_history
            return JsonResponse({
                'response': ai_response,
                'avatar_user': avatar_user,
                'avatar_assistant': avatar_assistant
            }, status=200)

        return JsonResponse({'error': 'Aucun message envoyé'}, status=400)

    # Contexte pour le template
    context = {
        'form': form,
        'chat_history': chat_history,
        'avatar_user': avatar_user,
        'avatar_assistant': avatar_assistant,
        'orders': orders,
        'order_items': order_items,
        'cart': cart,
        'cart_items': cart_items,
        'categories': categories,
        'list_products': list_products,
    }
    return render(request, 'chatbot.html', context)


def retrieve_response(user_input, chat_history, personal_info):
    # Structure des données personnelles
    structured_info = {
        "orders": [
            {"id": order.id, "status": order.status, "date": order.created_at}
            for order in personal_info.get('orders', [])
        ],
        "order_items": [
            {"order_id": item.order.id, "product": item.product.name, "quantity": item.quantity}
            for item in personal_info.get('order_items', [])
        ],
        "cart": {
            "id": personal_info.get('cart').id if personal_info.get('cart') else None,
            "items": [
                {"product": item.product.name, "quantity": item.quantity}
                for item in personal_info.get('cart_items', [])
            ]
        },
        "cart_items": [
            {"product": item.product.name, "quantity": item.quantity}
            for item in personal_info.get('cart_items', [])
        ],
        "categories": [category.name for category in personal_info.get('categories', [])],
        "products": [product.name for product in personal_info.get('list_products', [])],
    }

    # Gabarit pour le prompt
    template = """
    You are a helpful assistant. Structure your answers to be clear, organized, and easy to read.
    Use bullet points, proper formatting, and avoid unnecessary symbols like '**'.
    Personal information: {personal_info}
    Chat history: {chat_history}
    User question: {user_question}
    """
    prompt = ChatPromptTemplate.from_template(template)
    llm = ChatOpenAI(model="gpt-4", max_tokens=150, temperature=0.7)
    sequence = prompt | llm | StrOutputParser()

    response = sequence.invoke({
        "personal_info": structured_info,
        "chat_history": chat_history,
        "user_question": user_input,
    })

    return format_response(response)


def format_response(response):
    """
    Nettoie et structure la réponse pour une meilleure lisibilité.
    """
    # Remplace les caractères indésirables
    response = response.replace("**", "").strip()

    # Ajoute des retours à la ligne pour séparer les informations clés
    lines = response.split("-")
    structured_lines = [line.strip() for line in lines if line.strip()]
    return "\n".join(structured_lines)


def user_login(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        username = request.POST.get('username')
        login_method = request.POST.get('login-method')

        # Connexion par mot de passe
        if login_method == 'password':
            password = request.POST.get('password')
            if username and password:
                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)
                    messages.success(request, f"Aurevoir, {username}!")
                     # Mettre à jour la session avec la quantité totale d'articles dans le panier
                    cart = Cart.objects.filter(user=user, is_active=True).first()
                    if cart:
                       total_quantity = CartItem.objects.filter(cart=cart).aggregate(total_qty=Sum('quantity'))['total_qty']
                       request.session['cart_count'] = total_quantity if total_quantity else 0
                    else:
                       request.session['cart_count'] = 0

                    request.session.modified = True
                    return redirect('index')
                else:
                    messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
            else:
                messages.error(request, "Veuillez entrer tous les champs requis.")
        
        # Connexion par FaceID
        elif login_method == 'faceid':
            face_image = request.FILES.get('face_id')
            if username and face_image:
                try:
                    # Récupération de l'utilisateur et du profil
                    user = User.objects.get(username=username)
                    user_profile = UserProfile.objects.get(user=user)

                    if user_profile.face_id:
                        try:
                            known_image = face_recognition.load_image_file(user_profile.face_id.path)
                            unknown_image = face_recognition.load_image_file(face_image)
                            
                            known_encoding = face_recognition.face_encodings(known_image)
                            unknown_encoding = face_recognition.face_encodings(unknown_image)

                            if not known_encoding:
                                messages.error(request, "Erreur : l'image capturée n'est pas similaire.")
                            elif not unknown_encoding:
                                messages.error(request, "Erreur : l'image capturée n'est pas similaire.")
                            else:
                                # Comparaison par distance entre les encodages
                                face_distance = face_recognition.face_distance([known_encoding[0]], unknown_encoding[0])

                                if face_distance[0] <= 0.4:
                                    login(request, user)
                                    messages.success(request, f"Aurevoir, {username}!")
                                    # Mettre à jour la session avec la quantité totale d'articles dans le panier
                                    cart = Cart.objects.filter(user=user, is_active=True).first()
                                    if cart:
                                        total_quantity = CartItem.objects.filter(cart=cart).aggregate(total_qty=Sum('quantity'))['total_qty']
                                        request.session['cart_count'] = total_quantity if total_quantity else 0
                                    else:
                                        request.session['cart_count'] = 0

                                    request.session.modified = True
                                    return redirect('index')
                                else:
                                    messages.error(request, "Échec de la reconnaissance faciale. La distance entre les encodages est trop élevée.")
                        except Exception as e:
                            messages.error(request, f"Erreur lors de la vérification de FaceID : {e}")
                    else:
                        messages.error(request, "Aucun FaceID enregistré pour cet utilisateur.")
                except User.DoesNotExist:
                    messages.error(request, "Nom d'utilisateur incorrect.")
                except UserProfile.DoesNotExist:
                    messages.error(request, "Profil utilisateur non trouvé.")
            else:
                messages.error(request, "Veuillez entrer tous les champs requis.")
    
    return render(request, 'login.html',{'categories': categories})


def profile_view(request):
    categories = Category.objects.all()
    # Récupérer le profil utilisateur associé
    user_profile = get_object_or_404(UserProfile, user=request.user)

    return render(request, 'profile.html', {
        'num_tel': user_profile.num_tel,
        'face_id': user_profile.face_id,
        'email': user_profile.user.email,
        'address': user_profile.address,
        'categories': categories
    })


def deleteUser_View(request):
    try:
        current_user = request.user
        current_user.delete()
        return redirect('home')
    except:
        messages.error(request, "Erreur lors de la suppression de votre compte.")


@login_required
def confirm_deleteUser_View(request):
    categories = Category.objects.all()
    # Récupérer le profil de l'utilisateur
    user_profile = get_object_or_404(UserProfile, user=request.user)

    return render(request, "confirm_deleteUser.html", {
        'face_id': user_profile.face_id,'categories': categories 
    })

@login_required
def deleteUser_View(request):
    """ Supprime le compte de l'utilisateur connecté """
    user = request.user
    if request.method == 'POST':
        # Supprime l'utilisateur et déconnecte l'utilisateur
        user.delete()
        logout(request)  # Déconnecte l'utilisateur après suppression
        messages.success(request, "Votre compte a été supprimé avec succès.")
        return redirect('index')  # Redirection vers la page d'accueil ou de login
    else:
        messages.error(request, "Erreur lors de la suppression de votre compte.")
        return redirect('confirm_deleteUser')
    
@login_required
def edit_order(request, order_id):
    categories = Category.objects.all()
    # Récupérer la commande et vérifier qu'elle appartient à l'utilisateur
    order = get_object_or_404(Order, id=order_id, user=request.user)
    OrderItemFormset = modelformset_factory(OrderItem, fields=('quantity',), extra=0)
    

    if request.method == 'POST':
        formset = OrderItemFormset(request.POST, queryset=OrderItem.objects.filter(order=order))
    
        if formset.is_valid():
            formset.save()
            messages.success(request, "Votre commande a été mise à jour.")
            return redirect('user_orders')
    else:
        formset = OrderItemFormset(queryset=OrderItem.objects.filter(order=order))

    # Calcul du sous-total pour chaque produit et du total général
    order_items = OrderItem.objects.filter(order=order)
    total_price = Decimal(0.0)
    
    # Créer une liste de tuples (form, item) à passer au template
    form_item_pairs = []
    for form, item in zip(formset, order_items):
        item.subtotal = item.product.price * item.quantity
        total_price += item.subtotal
        form_item_pairs.append((form, item))

    context = {
        'order': order,
        'form_item_pairs': form_item_pairs,
        'total_price': total_price,
        'categories': categories, 
    }
    return render(request, 'edit_order.html', context)

@login_required
def user_orders(request):
    # Récupérer toutes les commandes de l'utilisateur connecté, triées par date de création
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    categories = Category.objects.all()

    # Ajouter des totaux calculés pour chaque commande
    for order in orders:
        # Calcul du prix total des articles
        order_items = order.items.all()  # Récupérer tous les items de la commande
        total_price = sum(item.product.price * item.quantity for item in order_items)

        # Calcul des taxes et frais de livraison
        taxes = total_price * Decimal('0.15')  # Taxe de 15%
        shipping_fee = Decimal('15.0')  # Frais de livraison fixes
        grand_total = total_price + taxes + shipping_fee

        # Ajouter ces valeurs comme attributs à l'objet order
        order.total_price = total_price
        order.taxes = taxes
        order.shipping_fee = shipping_fee
        order.grand_total = grand_total

    return render(request, 'user_orders.html', {'orders': orders, 'categories': categories})


@login_required
def updateAccount_view(request):
    # Récupération du profil de l'utilisateur actuel
    user_profile = UserProfile.objects.get(user=request.user)
    categories = Category.objects.all()

    if request.method == 'POST':
        # Formulaires pour mettre à jour les informations de l'utilisateur et du profil
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)

        if user_form.is_valid() and profile_form.is_valid():
            # Sauvegarde des données de l'utilisateur et du profil
            user_form.save()
            profile_form.save()

            messages.success(request, 'Votre compte a été mis à jour avec succès.')
            return redirect('profile')
    else:
        # Pré-remplir les formulaires avec les données existantes
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileForm(instance=user_profile)

    # Contexte pour passer les formulaires et les données du profil à la vue
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'num_tel': user_profile.num_tel, 
        'face_id': user_profile.face_id,
        'categories': categories,  
        'address': user_profile.address
    }
    return render(request, 'update_account.html', context)


def sales_statistics(request):
    categories = Category.objects.all()
    
    # Nombre total de commandes
    total_orders = Order.objects.count()

    # Nombre total de produits vendus
    total_products_sold = OrderItem.objects.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

    # Montant total des ventes
    total_sales = Order.objects.aggregate(total_revenue=Sum('total_price'))['total_revenue'] or 0

    # Nombre total d'utilisateurs
    total_users = User.objects.count()

    # Liste des produits les plus vendus (top 5) avec image
    top_selling_products = OrderItem.objects.values('product__name', 'product__image').annotate(total_sold=Sum('quantity')).order_by('-total_sold')[:5]

    # Passer les statistiques au template
    context = {
        'total_orders': total_orders,
        'total_products_sold': total_products_sold,
        'total_sales': total_sales,
        'total_users': total_users,
        'top_selling_products': top_selling_products,
        'categories': categories,
        'MEDIA_URL': settings.MEDIA_URL
    }

    return render(request, 'sales_statistics.html', context)


@login_required
def update_profile_picture(request):
    user_profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        form = ProfileImageForm(request.POST, request.FILES, instance=user_profile)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Votre image de profil a été mise à jour.")
            return redirect('profile')
        else:
            messages.error(request, "Erreur lors de la mise à jour de l'image de profil.")
    else:
        form = ProfileImageForm(instance=user_profile)
    
    return render(request, 'update_profile_picture.html', {'form': form, 'face_id': user_profile.face_id})

def user_logout(request):
    logout(request)
    request.session.flush()  
    messages.success(request, "Vous êtes déconnecté.")
    return redirect('login')  


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        # Utilisateur connecté, gérer le panier dans la base de données
        cart, created = Cart.objects.get_or_create(user=request.user, is_active=True)
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': 1, 'price': product.price}
        )
        if not item_created:
            cart_item.quantity += 1
            cart_item.save()
        # Mettre à jour la quantité totale pour les utilisateurs connectés
        total_quantity = CartItem.objects.filter(cart=cart).aggregate(total_qty=Sum('quantity'))['total_qty']
        request.session['cart_count'] = total_quantity if total_quantity else 0

    else:
        # Utilisateur non connecté, gérer le panier dans la session
        cart = request.session.get("cart", {})
        if str(product_id) in cart:
            cart[str(product_id)]['quantity'] += 1
        else:
            cart[str(product_id)] = {'quantity': 1, 'price': str(product.price)}

        # Sauvegarder le panier dans la session
        request.session['cart'] = cart
        # Calculer et mettre à jour le total des quantités dans le panier pour la session
        total_quantity = sum(item['quantity'] for item in cart.values())
        request.session['cart_count'] = total_quantity

    request.session.modified = True
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

# Page d'accueil avec liste des produits
def index(request):
    if 'cart_count' not in request.session:
        request.session['cart_count'] = 0
    products = Product.objects.all()
    categories = Category.objects.all() 
    return render(request, 'index.html', {'products': products, 'categories': categories})

# Page de détail d'un produit
def page_detail(request, id):
    product = get_object_or_404(Product, id=id)
    categories = Category.objects.all() 
    return render(request, 'page_detail.html', {'product': product, 'categories': categories})

# À propos
def about(request):
    categories = Category.objects.all()
    return render(request, 'about.html', {'categories': categories})

# Base
def base(request):
    return render(request, 'base.html')
    
   
# Liste des produits
def listProducts(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    return render(request, 'listProducts.html', {'categories': categories, 'products': products})

# Résultats de recherche
def search_results(request):
    query = request.GET.get('query')
    categories = Category.objects.all()
    if query:
        products = Product.objects.filter(name__icontains=query)
    else:
        products = Product.objects.all()
    return render(request, 'search_results.html', {'products': products, 'query': query, 'categories': categories})

def cart(request):
    # Initialisation des variables
    cart_items = []
    total_price = Decimal('0.00')
    categories = Category.objects.all()
    delivery_address = None  

    # Si l'utilisateur est authentifié, on récupère son panier actif et son adresse
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_active=True).first()
        if cart:
            cart_items = CartItem.objects.filter(cart=cart)

            # Calcul du prix total pour chaque produit et pour le panier entier
            for item in cart_items:
                item.total_item_price = item.product.price * item.quantity
                total_price += Decimal(item.total_item_price)

        # Récupération de l'adresse de livraison de l'utilisateur s'il est authentifié
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if user_profile:
            delivery_address = user_profile.address

    else:
        # Gestion pour les utilisateurs non authentifiés via session
        cart_session = request.session.get('cart', {})
        product_ids = list(cart_session.keys())
        products = Product.objects.filter(id__in=product_ids)

        for product in products:
            quantity = cart_session[str(product.id)]['quantity'] 
            total_item_price = product.price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total_item_price': total_item_price,
            })
            total_price += Decimal(total_item_price)

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'categories': categories,
        'delivery_address': delivery_address
    })

@login_required
def update_cart_quantity(request, product_id):
    if request.method == "POST":
        quantity = int(request.POST.get('quantity', 1))
        user = request.user
        product = get_object_or_404(Product, id=product_id)

        if user.is_authenticated:
            cart = Cart.objects.filter(user=user, is_active=True).first()
            if cart:
                cart_item = CartItem.objects.get(cart=cart, product=product)
                cart_item.quantity = quantity
                cart_item.save()

                # Mettre à jour le nombre total d'articles dans le panier
                total_quantity = CartItem.objects.filter(cart=cart).aggregate(total_qty=Sum('quantity'))['total_qty']
                request.session['cart_count'] = total_quantity
                request.session.modified = True

        return redirect('cart')
    
@login_required
def delete_product_of_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user = request.user

    # Récupérer le panier actif de l'utilisateur
    cart = Cart.objects.filter(user=user, is_active=True).first()

    if cart:
        try:
            # Récupérer l'élément du panier correspondant au produit
            cart_item = CartItem.objects.get(cart=cart, product=product)

            # Si la quantité est supérieure à 1, la décrémenter
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                # Si la quantité est 1 ou moins, supprimer l'élément du panier
                cart_item.delete()

            # Mettre à jour la quantité totale dans le panier
            total_quantity = CartItem.objects.filter(cart=cart).aggregate(total_qty=Sum('quantity'))['total_qty']
            request.session['cart_count'] = total_quantity if total_quantity else 0
            request.session.modified = True

            # Si le panier est vide, le désactiver
            if not CartItem.objects.filter(cart=cart).exists():
                cart.is_active = False
                cart.save()

        except CartItem.DoesNotExist:
            # Le produit n'existe pas dans le panier
            pass

    return redirect('cart')


def register(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)

        if form.is_valid():
            user = form.save()  
            login(request, user)  
            return redirect('index')  
    else:
        form = UserRegisterForm()

    return render(request, 'register.html', {'form': form,'categories': categories})

def products_by_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    categories = Category.objects.all()
    products = Product.objects.filter(category=category)
    return render(request, 'products_by_category.html', {'category': category, 'products': products,'categories': categories}) 

@login_required
def order(request):
    categories = Category.objects.all()
    cart_items = CartItem.objects.filter(cart__user=request.user, cart__is_active=True)

    # Récupérer le UserProfile de l'utilisateur connecté
    user_profile = get_object_or_404(UserProfile, user=request.user)

    # Calcul des prix
    total_price = Decimal(0.0)
    for item in cart_items:
        item.total_item_price = item.product.price * item.quantity
        total_price += item.total_item_price

    taxes = total_price * Decimal(0.15)
    shipping_fee = Decimal(15.0)
    grand_total = total_price + taxes + shipping_fee
    total_price_stripe = int(grand_total * 100)

    # Créer une session Stripe
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'cad',
                'product_data': {
                    'name': 'Commande',
                },
                'unit_amount': total_price_stripe,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/payment_success?session_id={CHECKOUT_SESSION_ID}'),
        cancel_url=request.build_absolute_uri('/order'),
    )

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'taxes': taxes,
        'shipping_fee': shipping_fee,
        'grand_total': grand_total,
        'stripe_session_id': session.id,
        'key': settings.STRIPE_PUBLIC_KEY,
        'categories': categories,
        'user_profile': user_profile,
    }

    return render(request, 'order.html', context)

def order_details(request, order_id):
    # Récupérer la commande en fonction de l'ID
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Récupérer les articles associés à cette commande
    order_items = OrderItem.objects.filter(order=order)

    # Calcul des totaux
    total_price = sum(item.product.price * item.quantity for item in order_items)
    taxes = total_price * Decimal('0.15') 
    shipping_fee = Decimal('15.0')  
    grand_total = total_price + taxes + shipping_fee

    context = {
        'order': order,
        'order_items': order_items,
        'total_price': total_price,
        'taxes': taxes,
        'shipping_fee': shipping_fee,
        'grand_total': grand_total,
    }

    return render(request, 'order_details.html', context)

@login_required
def delete_order(request, order_id):
    # Récupérer la commande en fonction de l'ID et vérifier qu'elle appartient à l'utilisateur
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Supprimer la commande
    order.delete()

    # Ajouter un message de succès
    messages.success(request, "La commande a été supprimée avec succès.")
    
    # Redirection vers la page des commandes de l'utilisateur
    return redirect('user_orders')


@login_required
def delete_order_item(request, product_id):
    # Filtrer les éléments de commande correspondant au produit et à l'utilisateur
    order_items = OrderItem.objects.filter(product_id=product_id, order__user=request.user)

    if order_items.exists():
        # Supprimer tous les éléments trouvés (ou vous pouvez en supprimer qu'un seul si besoin)
        order_items.delete()
        messages.success(request, "Le produit a été supprimé de votre commande.")
    else:
        messages.error(request, "Aucun article correspondant trouvé dans votre commande.")

    return redirect('user_orders')


@login_required
def edit_order(request, order_id):
    # Récupérer la commande et vérifier qu'elle appartient à l'utilisateur
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    categories = Category.objects.all()
    
    # Création du formset pour gérer les quantités d'articles de la commande
    OrderItemFormset = modelformset_factory(OrderItem, fields=('quantity',), extra=0)

    if request.method == 'POST':
        # Traiter les données soumises pour mettre à jour les quantités
        formset = OrderItemFormset(request.POST, queryset=OrderItem.objects.filter(order=order))
        
        if formset.is_valid():
            formset.save() 
            messages.success(request, "Votre commande a été mise à jour avec succès.")
            return redirect('user_orders') 
        else:
            messages.error(request, "Une erreur est survenue lors de la mise à jour de votre commande.")
    
    else:
        # Préparer le formset avec les données existantes si aucune modification n'a été envoyée
        formset = OrderItemFormset(queryset=OrderItem.objects.filter(order=order))

    # Calculer le sous-total pour chaque produit et le total de la commande
    order_items = OrderItem.objects.filter(order=order)
    total_price = 0 
    # Calcul du sous-total de chaque produit
    for item in order_items:
        item.subtotal = item.product.price * item.quantity
        total_price += item.subtotal  

    # Préparer le contexte pour le template
    context = {
        'item.subtotal':item.subtotal,
        'order': order,
        'formset': formset,
        'categories': categories,    
        'total_price': total_price,
        'form_item_pairs': zip(formset, order_items),  
    }

    return render(request, 'edit_order.html', context)

@login_required
def update_delivery_address(request):
    if request.method == "POST":
        new_address = request.POST.get('delivery_address')
        
        # Récupération ou création du profil de l'utilisateur
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Mise à jour de l'adresse
        if new_address:
            user_profile.address = new_address
            user_profile.save()
            messages.success(request, "Adresse de livraison mise à jour avec succès.")
        else:
            messages.error(request, "Adresse de livraison non valide.")

        return redirect('order') 
    
@login_required
def payment_success(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return redirect('order')  

    # Récupérer le panier actif de l'utilisateur
    cart = Cart.objects.filter(user=request.user, is_active=True).first()
    if not cart:
        return redirect('order') 

    # Récupération des articles du panier
    cart_items = CartItem.objects.filter(cart=cart)
    if not cart_items.exists():
        return redirect('order')  

    # Calculer le total
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    taxes = total_price * Decimal('0.15') 
    shipping_fee = Decimal('15.0')  
    grand_total = total_price + taxes + shipping_fee
    
    # Récupérer l'adresse de livraison
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        delivery_address = user_profile.address
    except UserProfile.DoesNotExist:
        delivery_address = "Adresse non définie"

    # Créer la commande
    order = Order.objects.create(
        user=request.user,
        total_price=grand_total,
        delivery_address = delivery_address,
        status='pending',
    )

    # Ajouter les articles du panier à la commande
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price,
        )

    # Réinitialiser le panier
    cart_items.delete()  
    cart.total_quantity = 0  
    cart.is_active = False 
    cart.save()

    # Réinitialiser le compteur dans la session
    request.session['cart_count'] = 0  

    # Obtenez la date et l'heure actuelles
    current_datetime = datetime.now()

    # Envoyer un email de confirmation
    send_mail(
        subject="Confirmation de votre commande",
        message=f"""
Bonjour {request.user.username},

Votre commande a été créée avec succès. Voici les détails :

- Numéro de commande : {order.id}
- Adresse de livraison : {order.delivery_address}
- Total payé : {order.total_price:.2f} $
- Date : {current_datetime.strftime('%d/%m/%Y %H:%M')}
- Statut : {order.get_status_display()}

Merci pour votre achat chez nous !

Cordialement,
L'équipe.
        """,
        from_email='pharellkamgue@gmail.com',
        recipient_list=[request.user.email],
        fail_silently=False,
    )

    # Rediriger vers une page de confirmation
    return render(request, 'payment_success.html', {
        'order': order,
    })


class CustomPasswordResetView(PasswordResetView):
    template_name = 'password_reset.html'    
    success_url = reverse_lazy('password_reset_done') 

    def form_valid(self, form):
        email = form.cleaned_data.get('email')  
        if not User.objects.filter(email=email).exists():
            # Si l'email n'existe pas, affiche une erreur sans envoyer d'email
            return render(self.request, self.template_name, {
                'form': form,
                'error': "Cette adresse e-mail n'est pas enregistrée dans notre système."
            })
        return super().form_valid(form)
