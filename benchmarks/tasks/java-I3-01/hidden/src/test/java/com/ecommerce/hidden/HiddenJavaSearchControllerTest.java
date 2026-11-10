package com.ecommerce.hidden;

import com.ecommerce.controller.ProductController;
import com.ecommerce.model.Product;
import com.ecommerce.repository.ProductRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ProductController.class)
@ContextConfiguration(classes = ProductController.class)
class HiddenJavaSearchControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ProductRepository productRepository;

    @Test
    void searchReturnsMatches() throws Exception {
        when(productRepository.searchByName("key")).thenReturn(List.of(new Product(7L, "Keyboard", "d", 1.0, 1, "c", "i")));
        mockMvc.perform(get("/api/products/search").param("q", "key"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].id").value(7));
    }

    @Test
    void blankQueryIsBadRequest() throws Exception {
        mockMvc.perform(get("/api/products/search").param("q", " ")).andExpect(status().isBadRequest());
        mockMvc.perform(get("/api/products/search")).andExpect(status().isBadRequest());
    }
}
