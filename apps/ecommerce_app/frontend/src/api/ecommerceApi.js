const API_BASE_URL = 'http://localhost:8080/api';

/**
 * Fetch products from the e-commerce store.
 * @param {string} [category] - Optional category filter.
 * @returns {Promise<Object[]>} - Promise resolving to an array of products.
 */
export async function fetchProducts(category) {
  let url = `${API_BASE_URL}/products`;
  if (category) {
    url += `?category=${encodeURIComponent(category)}`;
  }
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch products: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching products:', error);
    throw error;
  }
}

/**
 * Fetch a product by its ID.
 * @param {string} id - The product ID.
 * @returns {Promise<Object>} - Promise resolving to the product object.
 */
export async function fetchProductById(id) {
  const url = `${API_BASE_URL}/products/${encodeURIComponent(id)}`;
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch product: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching product:', error);
    throw error;
  }
}

/**
 * Submit a checkout request.
 * @param {Object} checkoutPayload - The checkout payload.
 * @returns {Promise<Object>} - Promise resolving to the checkout response.
 */
export async function submitCheckout(checkoutPayload) {
  const url = `${API_BASE_URL}/orders/checkout`;
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(checkoutPayload),
    });
    if (!response.ok) {
      throw new Error(`Checkout failed: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error submitting checkout:', error);
    throw error;
  }
}