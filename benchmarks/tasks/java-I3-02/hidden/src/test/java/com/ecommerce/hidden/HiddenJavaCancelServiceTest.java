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

class HiddenJavaCancelServiceTest {

    @Test
    void cancelRestoresStockAndRejectsTwice() {
        ProductRepository repo = new ProductRepository();
        Product p = repo.save(new Product(1L, "A", "d", 10.0, 10, "c", "i"));
        OrderService svc = new OrderService(repo);
        CheckoutRequest req = new CheckoutRequest();
        req.setCustomerName("N");
        req.setCustomerEmail("e@x.com");
        req.setShippingAddress("S");
        req.addItem(1L, 3);
        Order order = svc.createOrder(req);
        assertEquals(7, p.getStockQuantity());
        Order cancelled = svc.cancelOrder(order.getId());
        assertEquals("CANCELLED", cancelled.getStatus());
        assertEquals(10, p.getStockQuantity());
        assertThrows(IllegalStateException.class, () -> svc.cancelOrder(order.getId()));
        assertThrows(IllegalArgumentException.class, () -> svc.cancelOrder(424242L));
    }
}
