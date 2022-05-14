# import ssl
# import ldap3
#
# class Ldap:
#     """Class for LDAP related connections/operations."""
#
#     def __init__(self):
#         self.server = None
#         self.connection = None
#
#     def set_ldap_server_with_cert(self, endpoint_ip, port, root_ca):
#         try:
#             with open('ldap-root-ca-cert.cer', 'w') as f:
#                 f.write(root_ca)
#             tls = ldap3.Tls(validate=ssl.CERT_REQUIRED, ca_certs_file='ldap-root-ca-cert.cer')
#             self.server = ldap3.Server(endpoint_ip, port=port, use_ssl=True, tls=tls)
#             return True, "LDAP server is reachable"
#         except Exception as e:
#             return False, str(e)
#
#     def set_ldap_server_insecure(self, endpoint_ip, port):
#         try:
#             self.server = ldap3.Server(endpoint_ip, port=port)
#             return True, "LDAP Server is reachable"
#         except Exception as e:
#             return False, str(e)
#
#     def who_am_i(self):
#         return self.connection.extend.standard.who_am_i()
#
#     def set_ldap_connection(self, bindDN, bindPW):
#         try:
#             self.connection = ldap3.Connection(self.server, user=bindDN, password=bindPW, auto_bind=True)
#             server_info = self.who_am_i()
#             return True, server_info
#         except ldap3.core.exceptions.LDAPBindError as bind_error:
#             return False, str(bind_error)
#         except ldap3.core.exceptions.LDAPPasswordIsMandatoryError as pwd_mandatory_error:
#             return False, str(pwd_mandatory_error)
#         except Exception as e:
#             return False, str(e)
#
#     def ldap_user_search(self, user_search_base_dn, user_search_filter, user_search_username, test_user):
#         try:
#             if user_search_base_dn == "" or user_search_filter == "" or user_search_username == "":
#                 return True, "Skipping LDAP user search"
#             attribute_list = [user_search_username]
#             self.connection.search(search_base=user_search_base_dn, search_filter=user_search_filter,
#                                    attributes=attribute_list)
#             user_list = self.connection.entries
#             if test_user:
#                 for list_item in user_list:
#                     if str(list_item).__contains__(test_user):
#                         return True, "Found the test user: " + test_user + " successfully!"
#                     else:
#                         return False, "Test user: " + test_user + " is not found on performing a user search", user_list
#             else:
#                 return True, "Skipping User Search as no test user value passed"
#         except Exception as e:
#             return False, str(e)
#
#     def ldap_group_search(self, grp_search_base_dn, grp_search_filter, grp_search_user_attr,
#                           grp_search_grp_attr, grp_search_name_attr, test_group):
#         try:
#             if (grp_search_base_dn == "" and grp_search_filter == "" and grp_search_grp_attr == "" and
#                     grp_search_user_attr == "" and grp_search_name_attr == ""):
#                 return True, "Skipping LDAP group search"
#             attribute_list = []
#             if grp_search_user_attr:
#                 attribute_list.append(grp_search_user_attr)
#             if grp_search_grp_attr:
#                 attribute_list.append(grp_search_grp_attr)
#             if grp_search_name_attr:
#                 attribute_list.append(grp_search_name_attr)
#             if attribute_list.__len__() == 0:
#                 attribute_list = None
#
#             self.connection.search(search_base=grp_search_base_dn, search_filter=grp_search_filter,
#                                    attributes=attribute_list)
#             group_list = self.connection.entries
#             if test_group:
#                 for list_item in group_list:
#                     if str(list_item).__contains__(test_group):
#                         return True, "Found the test group: " + test_group + " successfully!"
#                     else:
#                         return False, "Test group: " + test_group + " is not found on performing a group search"
#             else:
#                 return True, "Skipping Group Search as no test group value passed"
#         except Exception as e:
#             return False, str(e)
#
#     def unbind_ldap_connection(self):
#         try:
#             self.connection.unbind()
#             return True, "Successfully disconnected from LDAP Server"
#         except Exception as e:
#             return False, str(e)
#
#
