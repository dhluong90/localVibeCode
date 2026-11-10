package com.ecommerce.hidden;

import com.ecommerce.dto.CheckoutRequest;
import com.ecommerce.model.Order;
import com.ecommerce.model.OrderItem;
import com.ecommerce.model.Product;
import com.ecommerce.repository.ProductRepository;
import com.ecommerce.service.OrderService;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;

class HiddenJavaI102Test {

    private static CheckoutRequest request() {
        CheckoutRequest req = new CheckoutRequest();
        req.setCustomerName("Ann");
        req.setCustomerEmail("ann@example.com");
        req.setShippingAddress("1 Main St");
        return req;
    }

    @Test
    void exactStockIsAvailable() {
        Product p = new Product(1L, "A", "d", 10.0, 5, "c", "i");
        assertTrue(p.hasStock(5));
        assertFalse(p.hasStock(6));
    }

    @Test
    void canOrderExactRemainingStock() {
        ProductRepository repo = new ProductRepository();
        Product p = repo.save(new Product(1L, "A", "d", 10.0, 5, "c", "i"));
        CheckoutRequest req = request();
        req.addItem(1L, 5);
        new OrderService(repo).createOrder(req);
        assertEquals(0, p.getStockQuantity());
    }
}
