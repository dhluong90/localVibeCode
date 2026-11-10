package com.ecommerce.repository;

import com.ecommerce.model.Product;
import org.springframework.stereotype.Repository;

import javax.annotation.PostConstruct;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Repository
public class ProductRepository {

    private final ConcurrentHashMap<Long, Product> products = new ConcurrentHashMap<>();
    private final AtomicLong idSequence = new AtomicLong(1);

    @PostConstruct
    public void init() {
        save(new Product("Wireless Noise-Cancelling Headphones", 99.99, 10, "Electronics"));
        save(new Product("Mechanical Keyboard", 149.50, 15, "Gaming"));
        save(new Product("Ergonomic Chair", 299.00, 5, "Furniture"));
        save(new Product("4K Monitor", 399.99, 8, "Electronics"));
    }

    public List<Product> findAll() {
        return new ArrayList<>(products.values());
    }

    public Optional<Product> findById(Long id) {
        return Optional.ofNullable(products.get(id));
    }

    public Product save(Product product) {
        if (product.getId() == null) {
            product.setId(idSequence.getAndIncrement());
        }
        products.put(product.getId(), product);
        return product;
    }

    public List<Product> searchByName(String keyword) {
        if (keyword == null || keyword.isBlank()) {
            return new ArrayList<>();
        }
        String needle = keyword.toLowerCase();
        return products.values().stream()
                .filter(product -> product.getName() != null && product.getName().toLowerCase().contains(needle))
                .sorted(java.util.Comparator.comparing(Product::getName))
                .collect(java.util.stream.Collectors.toList());
    }

    public List<Product> findByCategory(String category) {
        return products.values().stream()
                .filter(product -> category.equalsIgnoreCase(product.getCategory()))
                .toList();
    }
}