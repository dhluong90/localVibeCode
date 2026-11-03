import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import ProductGrid from './components/ProductGrid';
import CartDrawer from './components/CartDrawer';
import CheckoutModal from './components/CheckoutModal';
import { fetchProducts, submitCheckout } from './api/ecommerceApi';

const App = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [cart, setCart] = useState([]);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        const fetchedProducts = await fetchProducts(selectedCategory);
        setProducts(fetchedProducts);
      } catch (error) {
        console.error('Error fetching products:', error);
      } finally {
        setLoading(false);
      }
    };

    fetch();
  }, [selectedCategory]);

  const addToCart = (product) => {
    const existingItem = cart.find(item => item.product.id === product.id);
    if (existingItem) {
      setCart(cart.map(item => 
        item.product.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
      ));
    } else {
      setCart([...cart, { product, quantity: 1 }]);
    }
  };

  const updateQuantity = (productId, newQty) => {
    if (newQty <= 0) {
      setCart(cart.filter(item => item.product.id !== productId));
    } else {
      setCart(cart.map(item => 
        item.product.id === productId ? { ...item, quantity: newQty } : item
      ));
    }
  };

  const removeFromCart = (productId) => {
    setCart(cart.filter(item => item.product.id !== productId));
  };

  const handleCheckoutSubmit = async (formData) => {
    const payload = {
      items: cart.map(item => ({ productId: item.product.id, quantity: item.quantity })),
      ...formData
    };

    try {
      const response = await submitCheckout(payload);
      setOrderSuccess(response);
      setCart([]);
      setIsCheckoutOpen(false);
      alert('Order placed successfully!');
    } catch (error) {
      console.error('Error submitting checkout:', error);
      alert('Failed to place order. Please try again.');
    }
  };

  return (
    <div className="App">
      <Navbar 
        onSelectCategory={setSelectedCategory} 
        cartCount={cart.reduce((total, item) => total + item.quantity, 0)}
        onOpenCart={() => setIsCartOpen(!isCartOpen)}
      />
      <ProductGrid products={products} onAddToCart={addToCart} />
      <CartDrawer 
        isOpen={isCartOpen} 
        onClose={() => setIsCartOpen(false)} 
        cartItems={cart} 
        onUpdateQuantity={updateQuantity} 
        onRemoveItem={removeFromCart} 
        onProceedToCheckout={() => {
          setIsCartOpen(false);
          setIsCheckoutOpen(true);
        }}
      />
      <CheckoutModal 
        isOpen={isCheckoutOpen} 
        onClose={() => setIsCheckoutOpen(false)} 
        cartItems={cart}
        totalAmount={cart.reduce((total, item) => total + item.product.price * item.quantity, 0)}
        onSubmitOrder={handleCheckoutSubmit}
      />
    </div>
  );
};

export default App;