import React from 'react';

const Navbar = ({ cartCount, onOpenCart, onSelectCategory }) => {
  const categories = ['All', 'Audio', 'Peripherals', 'Displays', 'Furniture'];

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        ⚡ LocalVibe Store
      </div>
      <div className="navbar-categories">
        {categories.map(category => (
          <button
            key={category}
            onClick={() => onSelectCategory(category)}
            className="navbar-category-button"
          >
            {category}
          </button>
        ))}
      </div>
      <div className="navbar-cart">
        <button onClick={onOpenCart} className="navbar-cart-button">
          Cart <span className="navbar-cart-count">{cartCount}</span>
        </button>
      </div>
    </nav>
  );
};

export default Navbar;