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

class HiddenJavaM102Test {

    @Test
    void deductStockSubtracts() {
        Product p = new Product(1L, "A", "d", 10.0, 10, "c", "i");
        p.deductStock(3);
        assertEquals(7, p.getStockQuantity());
    }
}
