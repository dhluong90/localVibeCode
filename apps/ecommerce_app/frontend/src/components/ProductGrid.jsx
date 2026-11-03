import React from 'react';

const ProductCard = ({ product, onAddToCart }) => {
  const { name, category, description, price, stock } = product;
  const isOutOfStock = stock === 0;

  return (
    <div className="product-card">
      <h3>{name}</h3>
      <p><strong>Category:</strong> {category}</p>
      <p><strong>Description:</strong> {description}</p>
      <p><strong>Price:</strong> ${price.toFixed(2)}</p>
      <p><strong>Stock:</strong> {isOutOfStock ? 'Out of Stock' : 'In Stock'}</p>
      <button 
        onClick={() => onAddToCart(product)} 
        disabled={isOutOfStock}
      >
        Add to Cart
      </button>
    </div>
  );
};

const ProductGrid = ({ products, onAddToCart }) => {
  return (
    <div className="product-grid">
      {products.map(product => (
        <ProductCard key={product.id} product={product} onAddToCart={onAddToCart} />
      ))}
    </div>
  );
};

export default ProductGrid;