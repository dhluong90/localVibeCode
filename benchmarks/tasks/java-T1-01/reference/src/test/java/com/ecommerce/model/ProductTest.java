package com.ecommerce.model;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ProductTest {

    private static Product withStock(Integer stock) {
        return new Product(1L, "A", "d", 1.0, stock, "c", "i");
    }

    @Test
    void enoughStock() {
        assertTrue(withStock(10).hasStock(3));
    }

    @Test
    void exactStock() {
        assertTrue(withStock(3).hasStock(3));
    }

    @Test
    void insufficientStock() {
        assertFalse(withStock(2).hasStock(3));
    }

    @Test
    void nullStock() {
        assertFalse(withStock(null).hasStock(1));
    }

    @Test
    void deductReducesStock() {
        Product p = withStock(10);
        p.deductStock(4);
        assertEquals(6, p.getStockQuantity());
    }
}
