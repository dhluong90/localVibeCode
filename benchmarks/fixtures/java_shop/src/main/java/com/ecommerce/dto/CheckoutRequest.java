package com.ecommerce.dto;

import java.util.List;

public class CheckoutRequest {
    private String customerName;
    private String customerEmail;
    private String shippingAddress;
    private List<CheckoutItem> items;

    // Constructors
    public CheckoutRequest() {
    }

    public CheckoutRequest(String customerName, String customerEmail, String shippingAddress, List<CheckoutItem> items) {
        this.customerName = customerName;
        this.customerEmail = customerEmail;
        this.shippingAddress = shippingAddress;
        this.items = items;
    }

    // Getters and Setters
    public String getCustomerName() {
        return customerName;
    }

    public void setCustomerName(String customerName) {
        this.customerName = customerName;
    }

    public String getCustomerEmail() {
        return customerEmail;
    }

    public void setCustomerEmail(String customerEmail) {
        this.customerEmail = customerEmail;
    }

    public String getShippingAddress() {
        return shippingAddress;
    }

    public void setShippingAddress(String shippingAddress) {
        this.shippingAddress = shippingAddress;
    }

    public List<CheckoutItem> getItems() {
        return items;
    }

    public void addItem(Long productId, Integer quantity) {
        if (this.items == null) {
            this.items = new java.util.ArrayList<>();
        }
        this.items.add(new CheckoutItem(productId, quantity));
    }

    public void setItems(List<CheckoutItem> items) {
        this.items = items;
    }

    public static class CheckoutItem {
        private Long productId;
        private Integer quantity;

        // Constructors
        public CheckoutItem() {
        }

        public CheckoutItem(Long productId, Integer quantity) {
            this.productId = productId;
            this.quantity = quantity;
        }

        // Getters and Setters
        public Long getProductId() {
            return productId;
        }

        public void setProductId(Long productId) {
            this.productId = productId;
        }

        public Integer getQuantity() {
            return quantity;
        }

        public void setQuantity(Integer quantity) {
            this.quantity = quantity;
        }
    }
}