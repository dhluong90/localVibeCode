import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;

public class PreparedQuery {
  public ResultSet find(Connection c, String id) throws Exception {
    PreparedStatement ps = c.prepareStatement("SELECT * FROM users WHERE id = ?");
    ps.setString(1, id);
    return ps.executeQuery();
  }
}
