import React, { useState, useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom';
import Swal from 'sweetalert2'

import apiInstance from '../../utils/axios';
import UserData from '../plugin/UserData';
import Sidebar from './Sidebar';


function UpdateProduct() {
  const userData = UserData()
  const axios = apiInstance
  const param = useParams()


  const [product, setProduct] = useState([]);
  const [specifications, setSpecifications] = useState([{ title: '', content: '' }]);
  // No colours or clothing sizes here (Ayura). A pack size is "30 ml" or "50 g" and belongs to a
  // VARIANT, edited on "Sizes & stock" with its own price, MRP, net quantity, packed weight and
  // stock ledger. The old Size/Color rows were never read by pricing, stock, the cart or checkout.
  const [gallery, setGallery] = useState([{ image: null }]);
  const [category, setCategory] = useState([]);
  const [isLoading, setIsLoading] = useState(false)
  // Which tab is open. These used to be Bootstrap pills (data-bs-toggle), but the admin area
  // stopped loading Bootstrap's JavaScript in phase A, so nothing ever added the .active.show
  // that admin.css needs and every tab except the first was unreachable. React state instead.
  const [tab, setTab] = useState('basics')
  const paneClass = (name) => `tab-pane fade ${tab === name ? 'show active' : ''}`
  const tabClass = (name) => `nav-link ${tab === name ? 'active' : ''}`


  const navigate = useNavigate()

  // console.log("specifications: ", specifications)
  // console.log("colors: ", colors)
  // console.log("sizes: ", sizes)
  // console.log("gallery: ", gallery)

  const handleAddMore = (setStateFunction) => {
    setStateFunction((prevState) => [...prevState, {}]);
  };

  const handleRemove = (index, setStateFunction) => {
    setStateFunction((prevState) => {
      const newState = [...prevState];
      newState.splice(index, 1);
      return newState;
    });
  };

  const handleInputChange = (index, field, value, setStateFunction) => {
    setStateFunction((prevState) => {
      const newState = [...prevState];
      newState[index][field] = value;
      return newState;
    });
  };


  const handleImageChange = (index, event, setStateFunction) => {
    const file = event.target.files[0];

    if (file) {
      const reader = new FileReader();

      reader.onloadend = () => {
        setStateFunction((prevState) => {
          const newState = [...prevState];
          newState[index].image = { file, preview: reader.result };
          return newState;
        });
      };

      reader.readAsDataURL(file);
    } else {
      // Handle the case when no file is selected
      setStateFunction((prevState) => {
        const newState = [...prevState];
        newState[index].image = null; // Set image to null
        newState[index].preview = null; // Optionally set preview to null
        return newState;
      });
    }
  };


  const handleProductInputChange = (event) => {
    setProduct({
      ...product,
      [event.target.name]: event.target.value
    })
  };

  useEffect(() => {
    // Fetch product details from the backend
    const fetchProductDetails = () => {

      setProduct({
        ...product,
        image: product.image
      });
    };

    fetchProductDetails();
  }, []);



  // const handleProductFileChange = (event) => {

  //   const file = event.target.files[0];

  //   if (file) {
  //     const reader = new FileReader();

  //     reader.onloadend = () => {
  //       setProduct({
  //         ...product,
  //         image: {
  //           file: file,
  //           preview: reader.result
  //         }
  //       });
  //     };

  //     reader.readAsDataURL(file);
  //   } else {
  //     // Handle the case when no file is selected
  //     setProduct({
  //       ...product,
  //       image: product.image
  //     });
  //   }
  // };


  const handleProductFileChange = (event) => {
    const file = event.target.files[0];

    if (file) {
      setProduct({
        ...product,
        image: file,
      });
    } else {
      // Handle the case when no file is selected
      setProduct({
        ...product,
        image: null, // or whatever default value you want
      });
    }
  };

  useEffect(() => {
    const fetchCategory = async () => {
      axios.get('category/').then((res) => {
        setCategory(res.data)
      })
    }
    fetchCategory()
  }, [])


  useEffect(() => {
    const fetchProductItems = async () => {
      axios.get(`vendor-product-edit/${userData?.vendor_id}/${param.pid}/`).then((res) => {
        setProduct(res.data)
        // res.data.color and res.data.size are ignored: this screen no longer edits them.
        setSpecifications(res.data.specification)
        setGallery(res.data.gallery)
      })
    }
    fetchProductItems()
  }, [])


  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true)

    if (product.title == "" || product.description == "" || product.price == "" || product.category === null || product.shipping_amount == "" || product.image === null) {
      setIsLoading(false)
      console.log("Please fill in all required fields");
      Swal.fire({
        icon: 'warning',
        title: 'Missing Fields!',
        text: "All fields are required to create a product",
      })
      return;
    }

    try {
      setIsLoading(true)
      const formData = new FormData();

      // Values the API computes or that identify the row: the edit screen receives them but
      // must never send them back.
      const READ_ONLY_KEYS = [
        'id', 'sku', 'pid', 'slug', 'date', 'vendor', 'in_stock',
        'gallery', 'specification', 'size', 'color',
        'product_rating', 'rating_count', 'order_count', 'get_precentage',
      ];

      const isFile = (value) => value instanceof File || value instanceof Blob;

      // Append product data
      Object.entries(product)?.forEach(([key, value]) => {
        if (READ_ONLY_KEYS.includes(key)) return;
        if (value === null || value === undefined) return;

        if (key === 'image') {
          // Only send the image when the user picked a new one. Otherwise it is the URL string
          // the API returned, which is not a file and would be rejected.
          if (isFile(value)) {
            formData.append(key, value);
          } else if (value && isFile(value.file)) {
            formData.append(key, value.file);
          }
          return;
        }

        if (key === 'category') {
          // The API returns the whole category object; the form needs its id.
          const categoryId = typeof value === 'object' ? value?.id : value;
          if (categoryId !== undefined && categoryId !== null && categoryId !== '') {
            formData.append(key, categoryId);
          }
          return;
        }

        if (typeof value === 'object') return;
        formData.append(key, value);
      });

      // Append specifications data
      specifications?.forEach((specification, index) => {
        if (!specification?.title) return;
        formData.append(`specifications[${index}][title]`, specification.title);
        formData.append(`specifications[${index}][content]`, specification.content ?? '');
      });

      // No colors[] or sizes[] are sent. `size` and `color` are already in READ_ONLY_KEYS, and
      // the server only acts on those keys when they are present, so any rows a product already
      // has are left exactly as they are rather than being wiped.

      // Append gallery data
      gallery?.forEach((item, index) => {
        if (item?.image && isFile(item.image.file)) {
          // Newly picked file
          formData.append(`gallery[${index}][image]`, item.image.file, item.image.file.name);
        } else if (typeof item?.image === 'string' && item.image) {
          // Existing image: send its URL back so the server keeps it
          formData.append(`gallery[${index}][image]`, item.image);
        }
      });

      await apiInstance.patch(`vendor-product-edit/${userData?.vendor_id}/${param.pid}/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      Swal.fire({
        icon: 'success',
        title: 'Product Updated Successfully',
        text: 'This product has been successfully updated',
      });

      navigate('/admin-area/products/')
    } catch (error) {
      setIsLoading(false)
      const detail = error.response?.data;
      const firstError = detail && typeof detail === 'object'
        ? Object.entries(detail).map(([field, messages]) => `${field}: ${[].concat(messages).join(' ')}`).join('\n')
        : null;
      Swal.fire({
        icon: 'error',
        title: 'Product could not be updated',
        text: firstError || 'Something went wrong. Please try again.',
      });
    }
  };

  return (
    <div>
      <div className="container-fluid" id="main">
        <div className="row row-offcanvas row-offcanvas-left h-100">
          <Sidebar />
          {/*/col*/}
          <div className="col-md-9 col-lg-10 main mt-4">
            <div className="container">
              <form className="main-body" method='POST' encType="multipart/form-data" onSubmit={handleSubmit}>
                <div className="tab-content" id="pills-tabContent">
                  <div
                    className={paneClass('basics')}
                    id="pills-home"
                    role="tabpanel"
                    aria-labelledby="pills-home-tab"
                  >
                    <div className="row gutters-sm shadow p-4 rounded">
                      <h4 className="mb-4">Product Details</h4>
                      <div className="col-md-4 mb-3">
                        <div className="card h-100">
                          <div className="card-body">
                            <div className="d-flex flex-column align-items-center text-center">
                              {product.image && product.image.preview ? (
                                <img
                                  src={product.image.preview}
                                  alt="Product Thumbnail Preview"
                                  style={{ width: '100%', height: '200px', objectFit: 'cover', borderRadius: 10 }}
                                />
                              ) : (
                                <img
                                  src={product.image}
                                  style={{ width: '100%', height: '200px', objectFit: 'cover', borderRadius: 10 }}
                                  alt=""
                                />
                              )}

                              <div className="mt-3">
                                {product.title !== "" &&
                                  <h4 className="text-dark">{product.title}</h4>
                                }
                                {product.title === "" &&
                                  <h4 className="text-dark">Product Title</h4>
                                }
                              </div>
                            </div>
                            <div className="d-flex justify-content-center mt-4">
                              <Link to={`/detail/${product.slug}/`} className='btn btn-success mt-4'><i className='fas fa-eye'></i></Link>
                              <Link className='btn btn-danger mt-4 ms-2'><i className='fas fa-trash'></i></Link>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="col-md-8">
                        <div className="card mb-3">

                          <div className="card-body">

                            <div className="row text-dark">
                              <div className="col-lg-12 mb-2">
                                <label htmlFor="" className="mb-2">
                                  Product Thumbnail
                                </label>
                                <input
                                  type="file"
                                  className="form-control"
                                  name="image"
                                  id=""
                                  onChange={handleProductFileChange || product.image}
                                />
                              </div>
                              <div className="col-lg-12 mb-2 ">
                                <label htmlFor="" className="mb-2">
                                  Title
                                </label>
                                <input
                                  type="text"
                                  className="form-control"
                                  id=""
                                  name="title"
                                  value={product.title || ''}
                                  onChange={handleProductInputChange}
                                />
                              </div>
                              <div className="col-lg-12 mb-2">
                                <label htmlFor="" className="mb-2">
                                  Description
                                </label>
                                <textarea
                                  className="form-control"
                                  id=""
                                  cols={30}
                                  rows={10}
                                  defaultValue={""}
                                  name="description"
                                  value={product.description || ''}
                                  onChange={handleProductInputChange}
                                />
                              </div>
                              <div className="col-lg-6 mb-2">
                                <label htmlFor="" className="mb-2">
                                  Category
                                </label>
                                <select
                                  className="select form-control"
                                  id=""
                                  name="category"
                                  value={product.category || ''}
                                  onChange={handleProductInputChange}
                                >
                                  <option value="">- Select -</option>
                                  {category?.map((c, index) => (
                                    <option key={index} value={c.id}>{c.title}</option>
                                  ))}
                                </select>
                              </div>
                              <div className="col-lg-6 mb-2 ">
                                <label htmlFor="" className="mb-2">
                                  Brand
                                </label>
                                <input
                                  type="text"
                                  className="form-control"
                                  name="brand"
                                  value={product.brand || ''}
                                  onChange={handleProductInputChange}
                                />
                              </div>
                              <div className="col-lg-6 mb-2 ">
                                <label htmlFor="" className="mb-2">
                                  Sale Price
                                </label>
                                <input
                                  type="number"
                                  className="form-control"
                                  name="price"
                                  value={product.price || ''}
                                  onChange={handleProductInputChange}
                                />
                              </div>
                              <div className="col-lg-6 mb-2 ">
                                <label htmlFor="" className="mb-2">
                                  Regular Price
                                </label>
                                <input
                                  type="number"
                                  className="form-control"
                                  name="old_price"
                                  value={product.old_price || ''}
                                  onChange={handleProductInputChange}
                                />
                              </div>
                              <div className="col-lg-6 mb-2 ">
                                <label htmlFor="" className="mb-2">
                                  Shipping Amount
                                </label>
                                <input
                                  type="number"
                                  className="form-control"
                                  name="shipping_amount"
                                  value={product.shipping_amount || ''}
                                  onChange={handleProductInputChange}
                                />
                              </div>
                              <div className="col-lg-6 mb-2 ">
                                <label htmlFor="" className="mb-2">
                                  Available stock
                                </label>
                                {/* Stock comes from the inventory ledger and cannot be typed in here.
                                    To add stock, add a Batch in the admin (Inventory > Batches). */}
                                <input
                                  type="number"
                                  className="form-control"
                                  value={product.available_qty ?? 0}
                                  readOnly
                                  disabled
                                />
                                <small className="text-muted">From the stock ledger. Add stock by adding a batch in the admin.</small>
                              </div>
                              <div className="col-lg-12 mb-2 ">
                                <label htmlFor="" className="mb-2">
                                  Tags
                                </label>
                                <br />
                                <input
                                  type="text"
                                  className="form-control"
                                  name="tags"
                                  value={product.tags || ''}
                                  onChange={handleProductInputChange}
                                />
                                <span style={{ fontSize: 12 }} className='text-muted'>NOTE: Seperate tags with comma</span>

                              </div>
                            </div>

                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div
                    className={paneClass('gallery')}
                    id="pills-profile"
                    role="tabpanel"
                    aria-labelledby="pills-profile-tab"
                  >
                    <div className="row gutters-sm shadow p-4 rounded">
                      <h4 className="mb-4">Product Image</h4>
                      <div className="col-md-12">
                        <div className="card mb-3">
                          <div className="card-body">
                            {gallery?.map((item, index) => (

                              <div className="row text-dark mb-5">
                                <div className="col-lg-3">
                                  {/* {item.image && (
                                    <img
                                      src={item.image.preview}
                                      alt={`Preview for gallery item ${index + 1}`}
                                      style={{ width: '100%', height: '100px', objectFit: 'cover', borderRadius: 5 }}
                                    />
                                  )} */}

                                  {item.image && (item.image.preview ? (
                                    <img
                                      src={item.image.preview}
                                      alt="Product Thumbnail Preview"
                                      style={{ width: '100%', height: '100px', objectFit: 'cover', borderRadius: 10 }}
                                    />
                                  ) : (
                                    <img
                                      src={item.image}
                                      style={{ width: '100%', height: '100px', objectFit: 'cover', borderRadius: 10 }}
                                      alt=""
                                    />
                                  ))}
                                  {!item.image && (
                                    <img
                                      src="https://developers.elementor.com/docs/assets/img/elementor-placeholder-image.png"
                                      alt={`Preview for gallery item ${index + 1}`}
                                      style={{ width: '100%', height: '100px', objectFit: 'cover', borderRadius: 5 }}
                                    />
                                  )}
                                </div>
                                <div className="col-lg-6 mb-2">
                                  <label htmlFor="" className="mb-2">
                                    Product Image
                                  </label>
                                  <input
                                    type="file"
                                    className="form-control"
                                    name=""
                                    id=""
                                    onChange={(e) => handleImageChange(index, e, setGallery)}
                                  />
                                </div>
                                <div className="col-lg-3 mt-2">
                                  <button onClick={() => handleRemove(index, setGallery)} type='button' className='btn btn-danger mt-4'>Remove</button>
                                </div>

                              </div>
                            ))}

                            {gallery < 1 &&
                              <h4>No Images Selected</h4>
                            }

                            <button type='button' onClick={() => handleAddMore(setGallery)} className="btn btn-primary mt-2">
                              <i className="fas fa-plus" /> Add More Images
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div
                    className={paneClass('specs')}
                    id="pills-contact"
                    role="tabpanel"
                    aria-labelledby="pills-contact-tab"
                  >
                    <div className="row gutters-sm shadow p-4 rounded">
                      <h4 className="mb-4">Specifications</h4>
                      <div className="col-md-12">
                        <div className="card mb-3">
                          <div className="card-body">

                            {specifications?.map((specification, index) => (

                              <div className="row text-dark">
                                <div className="col-lg-3 mb-2">
                                  <label htmlFor="" className="mb-2">
                                    Title
                                  </label>
                                  <input
                                    type="text"
                                    className="form-control"
                                    value={specification.title || ''}
                                    onChange={(e) => handleInputChange(index, 'title', e.target.value, setSpecifications)}

                                  />
                                </div>
                                <div className="col-lg-6 mb-2">
                                  <label htmlFor="" className="mb-2">
                                    Content
                                  </label>
                                  <input
                                    type="text"
                                    className="form-control"
                                    value={specification.content || ''}
                                    onChange={(e) => handleInputChange(index, 'content', e.target.value, setSpecifications)}

                                  />
                                </div>
                                <div className="col-lg-3 mb-2">
                                  <button type='button' onClick={() => handleRemove(index, setSpecifications)} className='btn btn-danger mt-4'>Remove</button>
                                </div>
                              </div>
                            ))}

                            {specifications?.length < 1 &&
                              <h4>No Specification Form</h4>
                            }

                            <button type='button' onClick={() => handleAddMore(setSpecifications)} className="btn btn-primary mt-2">
                              <i className="fas fa-plus" /> Add More Specifications
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* The Sizes and Color tabs that stood here were from the multivendor
                      course this project started as. They edited rows nothing ever read. A
                      pack size ("30 ml", "50 g") is a VARIANT and lives on "Sizes & stock". */}
                  <div>
                    <ul
                      className="nav nav-pills mb-3 d-flex justify-content-center mt-5"
                      id="pills-tab"
                      role="tablist"
                    >
                      <li className="nav-item" role="presentation">
                        <button
                          className={tabClass('basics')}
                          id="pills-home-tab"
                          onClick={() => setTab('basics')}
                          type="button"
                          role="tab"
                          aria-controls="pills-home"
                          aria-selected={tab === 'basics'}
                        >
                          Basic Information
                        </button>
                      </li>
                      <li className="nav-item" role="presentation">
                        <button
                          className={tabClass('gallery')}
                          id="pills-profile-tab"
                          onClick={() => setTab('gallery')}
                          type="button"
                          role="tab"
                          aria-controls="pills-profile"
                          aria-selected={tab === 'gallery'}
                        >
                          Gallery
                        </button>
                      </li>
                      <li className="nav-item" role="presentation">
                        <button
                          className={tabClass('specs')}
                          id="pills-contact-tab"
                          onClick={() => setTab('specs')}
                          type="button"
                          role="tab"
                          aria-controls="pills-contact"
                          aria-selected={tab === 'specs'}
                        >
                          Specifications
                        </button>
                      </li>
                    </ul>
                    <div className="d-flex justify-content-center mb-5">
                      <button type='submit' className="btn btn-success w-50">
                        Create Product <i className="fa fa-check-circle" />{" "}
                      </button>
                    </div>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default UpdateProduct