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

class HiddenJavaSearchRepoTest {

    private static ProductRepository repo() {
        ProductRepository repo = new ProductRepository();
        repo.save(new Product(1L, "Mechanical Keyboard", "d", 10.0, 1, "c", "i"));
        repo.save(new Product(2L, "Wireless Mouse", "d", 10.0, 1, "c", "i"));
        repo.save(new Product(3L, "Gaming Keyboard", "d", 10.0, 1, "c", "i"));
        return repo;
    }

    @Test
    void caseInsensitiveContainsSortedByName() {
        List<String> names = repo().searchByName("KEYBOARD").stream().map(Product::getName).collect(Collectors.toList());
        assertEquals(List.of("Gaming Keyboard", "Mechanical Keyboard"), names);
    }

    @Test
    void blankOrNullReturnsEmpty() {
        assertTrue(repo().searchByName("  ").isEmpty());
        assertTrue(repo().searchByName(null).isEmpty());
    }

    @Test
    void noMatch() {
        assertTrue(repo().searchByName("chair").isEmpty());
    }
}
