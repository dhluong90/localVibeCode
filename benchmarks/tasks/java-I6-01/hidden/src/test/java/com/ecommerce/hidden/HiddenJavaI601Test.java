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

class HiddenJavaI601Test {

    @Test
    void newConstructorComputesSubtotal() {
        Product p = new Product(1L, "A", "d", 10.0, 10, "c", "i");
        assertEquals(30.0, new OrderItem(p, 3).getSubtotal(), 1e-9);
    }

    @Test
    void oldConstructorRemoved() {
        assertThrows(NoSuchMethodException.class,
                () -> OrderItem.class.getConstructor(Product.class, Integer.class, double.class));
    }

    @Test
    void orderTotalsUnchanged() {
        ProductRepository repo = new ProductRepository();
        repo.save(new Product(1L, "A", "d", 10.0, 10, "c", "i"));
        repo.save(new Product(2L, "B", "d", 2.5, 10, "c", "i"));
        CheckoutRequest req = new CheckoutRequest();
        req.setCustomerName("N");
        req.setCustomerEmail("e@x.com");
        req.setShippingAddress("S");
        req.addItem(1L, 2);
        req.addItem(2L, 4);
        Order order = new OrderService(repo).createOrder(req);
        assertEquals(30.0, order.getTotalAmount(), 1e-9);
        assertEquals(10.0, order.getItems().get(1).getSubtotal(), 1e-9);
    }
}
