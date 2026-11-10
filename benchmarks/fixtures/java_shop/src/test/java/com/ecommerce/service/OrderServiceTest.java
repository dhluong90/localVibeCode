package com.ecommerce.service;

import com.ecommerce.dto.CheckoutRequest;
import com.ecommerce.model.Order;
import com.ecommerce.model.Product;
import com.ecommerce.repository.ProductRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.util.Collections;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class OrderServiceTest {

    @Mock
    private ProductRepository productRepository;

    @InjectMocks
    private OrderService orderService;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    public void testCreateOrderSuccess() {
        // Arrange
        Product product = new Product(1L, "Product 1", "Description", 10.0, 10, "Category", "Brand");
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        CheckoutRequest request = new CheckoutRequest();
        request.setCustomerName("John Doe");
        request.setCustomerEmail("john@example.com");
        request.setShippingAddress("123 Main St");
        request.addItem(1L, 2);

        // Act
        Order order = orderService.createOrder(request);

        // Assert
        assertNotNull(order);
        assertEquals("CONFIRMED", order.getStatus());
        assertEquals(20.0, order.getTotalAmount());
        assertEquals(8, product.getStockQuantity());
    }

    @Test
    public void testCreateOrderInsufficientStock() {
        // Arrange
        Product product = new Product(1L, "Product 1", "Description", 10.0, 10, "Category", "Brand");
        when(productRepository.findById(1L)).thenReturn(Optional.of(product));

        CheckoutRequest request = new CheckoutRequest();
        request.setCustomerName("John Doe");
        request.setCustomerEmail("john@example.com");
        request.setShippingAddress("123 Main St");
        request.addItem(1L, 9999);

        // Act & Assert
        assertThrows(IllegalStateException.class, () -> orderService.createOrder(request));
    }

    @Test
    public void testCreateOrderEmptyCart() {
        // Arrange
        CheckoutRequest request = new CheckoutRequest();
        request.setItems(Collections.emptyList());

        // Act & Assert
        assertThrows(IllegalArgumentException.class, () -> orderService.createOrder(request));
    }
}