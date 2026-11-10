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

class HiddenJavaI101Test {

    private static CheckoutRequest request() {
        CheckoutRequest req = new CheckoutRequest();
        req.setCustomerName("Ann");
        req.setCustomerEmail("ann@example.com");
        req.setShippingAddress("1 Main St");
        return req;
    }

    @Test
    void totalIsSumOfAllItems() {
        ProductRepository repo = new ProductRepository();
        repo.save(new Product(1L, "A", "d", 10.0, 10, "c", "i"));
        repo.save(new Product(2L, "B", "d", 5.0, 10, "c", "i"));
        CheckoutRequest req = request();
        req.addItem(1L, 2);
        req.addItem(2L, 3);
        Order order = new OrderService(repo).createOrder(req);
        assertEquals(35.0, order.getTotalAmount(), 1e-9);
    }
}
