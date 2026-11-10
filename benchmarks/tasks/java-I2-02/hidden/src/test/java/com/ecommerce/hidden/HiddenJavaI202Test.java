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

class HiddenJavaI202Test {

    private static Order place(OrderService svc, String email) {
        CheckoutRequest req = new CheckoutRequest();
        req.setCustomerName("N");
        req.setCustomerEmail(email);
        req.setShippingAddress("S");
        req.addItem(1L, 1);
        return svc.createOrder(req);
    }

    @Test
    void filtersByEmailCaseInsensitiveSortedById() {
        ProductRepository repo = new ProductRepository();
        repo.save(new Product(1L, "A", "d", 10.0, 100, "c", "i"));
        OrderService svc = new OrderService(repo);
        Order a = place(svc, "Ann@Example.com");
        place(svc, "bob@example.com");
        Order c = place(svc, "ann@example.com");
        List<Long> ids = svc.getOrdersByCustomerEmail("ANN@example.com").stream().map(Order::getId).collect(Collectors.toList());
        assertEquals(List.of(a.getId(), c.getId()), ids);
        assertTrue(svc.getOrdersByCustomerEmail("nobody@example.com").isEmpty());
    }
}
