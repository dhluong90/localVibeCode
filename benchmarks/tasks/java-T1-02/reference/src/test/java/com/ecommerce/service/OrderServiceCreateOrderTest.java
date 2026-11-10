package com.ecommerce.service;

import com.ecommerce.dto.CheckoutRequest;
import com.ecommerce.model.Order;
import com.ecommerce.model.Product;
import com.ecommerce.repository.ProductRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

class OrderServiceCreateOrderTest {

    private ProductRepository repo;
    private OrderService svc;
    private Product a;

    @BeforeEach
    void setUp() {
        repo = new ProductRepository();
        a = repo.save(new Product(1L, "A", "d", 10.0, 10, "c", "i"));
        repo.save(new Product(2L, "B", "d", 5.0, 10, "c", "i"));
        svc = new OrderService(repo);
    }

    private static CheckoutRequest request() {
        CheckoutRequest req = new CheckoutRequest();
        req.setCustomerName("N");
        req.setCustomerEmail("e@x.com");
        req.setShippingAddress("S");
        return req;
    }

    @Test
    void multiItemTotal() {
        CheckoutRequest req = request();
        req.addItem(1L, 2);
        req.addItem(2L, 3);
        assertEquals(35.0, svc.createOrder(req).getTotalAmount(), 1e-9);
    }

    @Test
    void deductsStock() {
        CheckoutRequest req = request();
        req.addItem(1L, 4);
        svc.createOrder(req);
        assertEquals(6, a.getStockQuantity());
    }

    @Test
    void insufficientStock() {
        CheckoutRequest req = request();
        req.addItem(1L, 11);
        assertThrows(IllegalStateException.class, () -> svc.createOrder(req));
    }

    @Test
    void unknownProduct() {
        CheckoutRequest req = request();
        req.addItem(99L, 1);
        assertThrows(IllegalArgumentException.class, () -> svc.createOrder(req));
    }

    @Test
    void emptyCart() {
        CheckoutRequest req = request();
        req.setItems(Collections.emptyList());
        assertThrows(IllegalArgumentException.class, () -> svc.createOrder(req));
    }

    @Test
    void blankCustomer() {
        CheckoutRequest req = request();
        req.setCustomerName(" ");
        req.addItem(1L, 1);
        assertThrows(IllegalArgumentException.class, () -> svc.createOrder(req));
    }
}
