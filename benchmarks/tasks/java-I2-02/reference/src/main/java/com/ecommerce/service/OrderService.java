package com.ecommerce.service;

import com.ecommerce.dto.CheckoutRequest;
import com.ecommerce.model.Order;
import com.ecommerce.model.OrderItem;
import com.ecommerce.model.Product;
import com.ecommerce.repository.ProductRepository;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class OrderService {

    private final ProductRepository productRepository;
    private final ConcurrentHashMap<Long, Order> orderMap = new ConcurrentHashMap<>();
    private final AtomicLong orderIdSeq = new AtomicLong(1000);

    public OrderService(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    public synchronized Order createOrder(CheckoutRequest request) {
        if (request.getItems().isEmpty()) {
            throw new IllegalArgumentException("Cart cannot be empty");
        }

        if (request.getCustomerName().isBlank() || request.getCustomerEmail().isBlank() || request.getShippingAddress().isBlank()) {
            throw new IllegalArgumentException("Customer name, email, and shipping address cannot be blank");
        }

        List<OrderItem> orderItems = new ArrayList<>();
        double totalAmount = 0.0;

        for (CheckoutRequest.CheckoutItem item : request.getItems()) {
            Product product = productRepository.findById(item.getProductId())
                    .orElseThrow(() -> new IllegalArgumentException("Product not found: " + item.getProductId()));

            if (!product.hasStock(item.getQuantity())) {
                throw new IllegalStateException("Insufficient stock for product: " + product.getName());
            }

            product.deductStock(item.getQuantity());
            double subtotal = product.getPrice() * item.getQuantity();
            orderItems.add(new OrderItem(product, item.getQuantity(), subtotal));
            totalAmount += subtotal;
        }

        Order order = new Order(orderIdSeq.incrementAndGet(), request.getCustomerName(), request.getCustomerEmail(),
                request.getShippingAddress(), orderItems, totalAmount, "CONFIRMED");
        orderMap.put(order.getId(), order);

        return order;
    }

    public Order getOrderById(Long id) {
        return orderMap.get(id);
    }

    public List<Order> getOrdersByCustomerEmail(String email) {
        List<Order> result = new ArrayList<>();
        for (Order order : orderMap.values()) {
            if (order.getCustomerEmail() != null && order.getCustomerEmail().equalsIgnoreCase(email)) {
                result.add(order);
            }
        }
        result.sort(java.util.Comparator.comparing(Order::getId));
        return result;
    }

    public List<Order> getAllOrders() {
        return new ArrayList<>(orderMap.values());
    }
}