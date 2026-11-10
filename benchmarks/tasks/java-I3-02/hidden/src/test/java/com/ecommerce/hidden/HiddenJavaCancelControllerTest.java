package com.ecommerce.hidden;

import com.ecommerce.controller.OrderController;
import com.ecommerce.model.Order;
import com.ecommerce.service.OrderService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(OrderController.class)
@ContextConfiguration(classes = OrderController.class)
class HiddenJavaCancelControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private OrderService orderService;

    @Test
    void cancelOk() throws Exception {
        Order order = new Order();
        order.setId(1L);
        order.setStatus("CANCELLED");
        when(orderService.cancelOrder(1L)).thenReturn(order);
        mockMvc.perform(post("/api/orders/1/cancel"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("CANCELLED"));
    }

    @Test
    void cancelNotFound() throws Exception {
        when(orderService.cancelOrder(2L)).thenThrow(new IllegalArgumentException("nf"));
        mockMvc.perform(post("/api/orders/2/cancel")).andExpect(status().isNotFound());
    }

    @Test
    void cancelTwiceConflict() throws Exception {
        when(orderService.cancelOrder(3L)).thenThrow(new IllegalStateException("dup"));
        mockMvc.perform(post("/api/orders/3/cancel")).andExpect(status().isConflict());
    }
}
