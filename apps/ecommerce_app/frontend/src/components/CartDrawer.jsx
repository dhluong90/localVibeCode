import React from 'react';

const CartDrawer = ({ isOpen, onClose, cartItems, onUpdateQuantity, onRemoveItem, onProceedToCheckout }) => {
  if (!isOpen) return null;

  const totalAmount = cartItems.reduce((total, item) => total + item.product.price * item.quantity, 0);

  return (
    <div className="cart-drawer-overlay" onClick={onClose}>
      <div className="cart-drawer" onClick={(e) => e.stopPropagation()}>
        <h2>Shopping Cart</h2>
        <ul className="cart-items">
          {cartItems.map((item) => (
            <li key={item.product.id} className="cart-item">
              <div className="cart-item-info">
                <span>{item.product.name}</span>
                <span>${item.product.price.toFixed(2)}</span>
              </div>
              <div className="cart-item-quantity">
                <button onClick={() => onUpdateQuantity(item.product.id, item.quantity - 1)}>-</button>
                <span>{item.quantity}</span>
                <button onClick={() => onUpdateQuantity(item.product.id, item.quantity + 1)}>+</button>
              </div>
              <button className="cart-item-remove" onClick={() => onRemoveItem(item.product.id)}>Remove</button>
            </li>
          ))}
        </ul>
        <div className="cart-total">
          <span>Total:</span>
          <span>${totalAmount.toFixed(2)}</span>
        </div>
        <button
          className="cart-proceed-to-checkout"
          onClick={onProceedToCheckout}
          disabled={cartItems.length === 0}
        >
          Proceed to Checkout
        </button>
      </div>
    </div>
  );
};

export default CartDrawer;